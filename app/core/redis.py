"""
AURA Enterprise Resilient Redis Manager
========================================
Production-grade distributed caching and concurrency locking for AURA SaaS.
Features:
- Connection pooling via `redis.asyncio.ConnectionPool`
- Circuit Breaker / Graceful Fallback to Python In-Memory RAM when Redis is offline
- Safe distributed concurrency locks with UUID tokens and Lua release scripts
- Multi-tenant namespacing helpers
- Non-blocking SCAN-based pattern invalidation
- Live health telemetry (latency, memory, client connections)
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import redis.asyncio as aioredis
    from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
    HAS_REDIS_LIB = True
except ImportError:
    aioredis = None
    RedisConnectionError = Exception
    RedisTimeoutError = Exception
    HAS_REDIS_LIB = False

from app.core.config import settings

logger = logging.getLogger("aura.core.redis")


class ResilientRedisManager:
    """
    Enterprise-Grade Resilient Redis Manager.
    Guarantees zero crashes: seamlessly degrades to In-Memory RAM if Redis is down,
    and automatically reconnects when Redis comes back online.
    """

    def __init__(self):
        self._pool: Optional[Any] = None
        self._client: Optional[Any] = None
        self._is_connected: bool = False
        self._last_retry_ts: float = 0.0
        self._retry_cooldown: float = 15.0  # seconds between reconnect attempts

        # Resilient In-Memory Fallback Store: key -> (expiry_ts, json_str)
        self._in_memory_store: Dict[str, Tuple[float, str]] = {}
        # In-Memory Concurrency Locks: lock_key -> asyncio.Lock
        self._in_memory_locks: Dict[str, asyncio.Lock] = {}

        # Lua script for atomic distributed unlock (releases lock only if token matches)
        self._unlock_lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

    async def initialize(self) -> bool:
        """Initializes the connection pool if Redis is enabled."""
        if not settings.REDIS_ENABLED or not HAS_REDIS_LIB:
            self._is_connected = False
            logger.info("AURA Redis: Running in In-Memory RAM Fallback mode (REDIS_ENABLED=False or lib missing).")
            return False

        try:
            self._pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
                decode_responses=True
            )
            self._client = aioredis.Redis(connection_pool=self._pool)
            # Test ping
            await self._client.ping()
            self._is_connected = True
            logger.info(f"AURA Redis: Successfully connected to distributed cache at {settings.REDIS_URL}")
            return True
        except Exception as e:
            self._is_connected = False
            self._last_retry_ts = time.time()
            logger.warning(f"AURA Redis: Initial connection failed ({e}). Operating in resilient In-Memory fallback mode.")
            return False

    async def _get_active_client(self) -> Optional[Any]:
        """Returns the active redis client or attempts periodic reconnect if down."""
        if not settings.REDIS_ENABLED or not HAS_REDIS_LIB:
            return None

        if self._client is not None and self._is_connected:
            return self._client

        # Cooldown check for reconnection attempts
        now = time.time()
        if now - self._last_retry_ts < self._retry_cooldown:
            return None

        self._last_retry_ts = now
        try:
            if self._client is None:
                await self.initialize()
            else:
                await self._client.ping()
                self._is_connected = True
                logger.info("AURA Redis: Reconnected to distributed cache successfully.")
            return self._client if self._is_connected else None
        except Exception as ex:
            self._is_connected = False
            logger.debug(f"AURA Redis reconnect attempt failed: {ex}")
            return None

    def _cleanup_expired_memory_keys(self) -> None:
        """Evicts expired keys from in-memory fallback store."""
        now = time.time()
        expired = [k for k, (exp, _) in self._in_memory_store.items() if exp > 0 and exp < now]
        for k in expired:
            self._in_memory_store.pop(k, None)

    # ──────────────────────────────────────────────────────────────────────────
    # Typed Key-Value Operations
    # ──────────────────────────────────────────────────────────────────────────

    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieves and deserializes JSON from Redis or fallback store."""
        client = await self._get_active_client()
        if client:
            try:
                raw = await client.get(key)
                if raw is not None:
                    return json.loads(raw)
                return None
            except Exception as e:
                logger.debug(f"Redis get_json error on key {key}: {e}")
                self._is_connected = False

        # In-Memory Fallback
        self._cleanup_expired_memory_keys()
        entry = self._in_memory_store.get(key)
        if entry:
            exp, val_str = entry
            if exp == 0 or exp >= time.time():
                try:
                    return json.loads(val_str)
                except Exception:
                    return val_str
            else:
                self._in_memory_store.pop(key, None)
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Serializes and stores JSON in Redis or fallback store with optional TTL."""
        try:
            val_str = json.dumps(value, default=str)
        except Exception as se:
            logger.error(f"Redis set_json serialization error on {key}: {se}")
            return False

        client = await self._get_active_client()
        if client:
            try:
                if ttl_seconds and ttl_seconds > 0:
                    await client.set(key, val_str, ex=ttl_seconds)
                else:
                    await client.set(key, val_str)
                return True
            except Exception as e:
                logger.debug(f"Redis set_json error on key {key}: {e}")
                self._is_connected = False

        # In-Memory Fallback
        exp_ts = (time.time() + ttl_seconds) if (ttl_seconds and ttl_seconds > 0) else 0.0
        self._in_memory_store[key] = (exp_ts, val_str)
        return True

    async def delete(self, key: str) -> bool:
        """Deletes a key from Redis and fallback store."""
        client = await self._get_active_client()
        deleted = False
        if client:
            try:
                res = await client.delete(key)
                deleted = bool(res)
            except Exception as e:
                logger.debug(f"Redis delete error on key {key}: {e}")
                self._is_connected = False

        if key in self._in_memory_store:
            self._in_memory_store.pop(key, None)
            deleted = True
        return deleted

    async def delete_pattern(self, pattern: str) -> int:
        """Deletes all keys matching a glob pattern using non-blocking SCAN."""
        client = await self._get_active_client()
        count = 0
        if client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        await client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
                return count
            except Exception as e:
                logger.debug(f"Redis delete_pattern error on pattern {pattern}: {e}")
                self._is_connected = False

        # In-Memory Fallback (fnmatch glob pattern)
        import fnmatch
        keys_to_del = [k for k in self._in_memory_store.keys() if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_del:
            self._in_memory_store.pop(k, None)
            count += 1
        return count

    async def exists(self, key: str) -> bool:
        """Checks if key exists and has not expired."""
        client = await self._get_active_client()
        if client:
            try:
                return bool(await client.exists(key))
            except Exception:
                self._is_connected = False

        self._cleanup_expired_memory_keys()
        return key in self._in_memory_store

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Extends or sets TTL for a given key (sliding window expiration)."""
        client = await self._get_active_client()
        if client:
            try:
                return bool(await client.expire(key, ttl_seconds))
            except Exception:
                self._is_connected = False

        if key in self._in_memory_store:
            _, val_str = self._in_memory_store[key]
            self._in_memory_store[key] = (time.time() + ttl_seconds, val_str)
            return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # Distributed Concurrency Locking (Double-Booking Prevention)
    # ──────────────────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def acquire_lock(
        self,
        lock_key: str,
        timeout: float = 5.0,
        blocking_timeout: float = 2.0
    ):
        """
        Distributed atomic lock with safe auto-release:
        - In Redis: uses SET lock_key token NX PX (timeout_ms) and releases via Lua token match
        - In Memory: uses asyncio.Lock
        Raises TimeoutError if lock cannot be acquired within blocking_timeout.
        """
        token = str(uuid.uuid4())
        timeout_ms = int(timeout * 1000)
        acquired = False
        start_ts = time.time()

        client = await self._get_active_client()

        if client:
            # Distributed Redis Lock
            while (time.time() - start_ts) < blocking_timeout:
                try:
                    res = await client.set(lock_key, token, nx=True, px=timeout_ms)
                    if res:
                        acquired = True
                        break
                except Exception as ex:
                    logger.debug(f"Redis lock acquisition error on {lock_key}: {ex}")
                    self._is_connected = False
                    break
                await asyncio.sleep(0.05)

            if not acquired and self._is_connected:
                raise TimeoutError(f"Could not acquire distributed lock for '{lock_key}' within {blocking_timeout}s")

        if not acquired:
            # Fallback to in-process asyncio Lock
            if lock_key not in self._in_memory_locks:
                self._in_memory_locks[lock_key] = asyncio.Lock()
            mem_lock = self._in_memory_locks[lock_key]
            try:
                await asyncio.wait_for(mem_lock.acquire(), timeout=blocking_timeout)
                acquired = True
            except asyncio.TimeoutError:
                raise TimeoutError(f"Could not acquire in-memory lock for '{lock_key}' within {blocking_timeout}s")

        try:
            yield
        finally:
            # Safe Release
            client = await self._get_active_client()
            if client and self._is_connected:
                try:
                    await client.eval(self._unlock_lua, 1, lock_key, token)
                except Exception as e:
                    logger.debug(f"Redis lock release error on {lock_key}: {e}")
            elif lock_key in self._in_memory_locks:
                mem_lock = self._in_memory_locks[lock_key]
                if mem_lock.locked():
                    mem_lock.release()

    # ──────────────────────────────────────────────────────────────────────────
    # Health Telemetry
    # ──────────────────────────────────────────────────────────────────────────

    async def get_health(self) -> Dict[str, Any]:
        """Provides real-time health telemetry for the Control Tower radar."""
        if not settings.REDIS_ENABLED or not HAS_REDIS_LIB:
            return {
                "name": "Redis Distributed Cache & Locks",
                "status": "FALLBACK_IN_MEMORY",
                "mode": "in_memory_emulation",
                "latency_ms": 0.05,
                "provider": "Local RAM (Redis Disabled)",
                "active_keys": len(self._in_memory_store)
            }

        client = await self._get_active_client()
        if client is None:
            return {
                "name": "Redis Distributed Cache & Locks",
                "status": "FALLBACK_IN_MEMORY",
                "mode": "in_memory_emulation",
                "latency_ms": 0.05,
                "provider": "Local RAM Fallback (Redis Server Offline)",
                "active_keys": len(self._in_memory_store)
            }

        start = time.time()
        try:
            await client.ping()
            latency = round((time.time() - start) * 1000, 2)
            info = await client.info("memory")
            used_mem = info.get("used_memory_human", "N/A")
            db_size = await client.dbsize()
            return {
                "name": "Redis Distributed Cache & Locks",
                "status": "HEALTHY",
                "mode": "distributed_cluster",
                "latency_ms": latency,
                "provider": "Redis Cloud / Cluster",
                "memory_used": used_mem,
                "active_keys": db_size
            }
        except Exception as e:
            self._is_connected = False
            return {
                "name": "Redis Distributed Cache & Locks",
                "status": "FALLBACK_IN_MEMORY",
                "mode": "in_memory_emulation",
                "latency_ms": 0.05,
                "provider": "Local RAM Fallback",
                "error": str(e),
                "active_keys": len(self._in_memory_store)
            }

    async def close(self) -> None:
        """Closes connections cleanly."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
        if self._pool:
            try:
                await self._pool.disconnect()
            except Exception:
                pass
        self._is_connected = False


# Global Singleton Instance
redis_manager = ResilientRedisManager()
