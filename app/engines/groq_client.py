"""
AURA Groq High-Speed LLM Client
================================
Provides sub-second, enterprise-grade AI chat completions with native tool calling
via Groq cloud inference engine (qwen/qwen3.8-27b).
Zero 429 quota exhaustion, ultra-low latency, and OpenAI-compatible protocol.
"""

import json
import logging
from typing import Optional, Dict, Any, List
import httpx
from app.core.config import settings

logger = logging.getLogger("aura.groq.client")


class GroqClient:
    """
    High-speed LLM engine client for AURA Copilot using Groq API.
    """
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    @classmethod
    def is_configured(cls) -> bool:
        """Returns True if a valid Groq API key is present."""
        key = getattr(settings, "GROQ_API_KEY", "") or ""
        return bool(key.strip() and key.startswith("gsk_"))

    @classmethod
    def get_model(cls) -> str:
        """Returns the configured Groq model or default."""
        return getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b") or "qwen/qwen3.8-27b"

    @classmethod
    def _normalize_schema(cls, o: Any) -> Any:
        """Recursively normalizes uppercase JSON schema types to valid standard lowercase types."""
        if isinstance(o, dict):
            return {
                k: (v.lower() if k == "type" and isinstance(v, str) else cls._normalize_schema(v))
                for k, v in o.items()
            }
        if isinstance(o, list):
            return [cls._normalize_schema(x) for x in o]
        return o

    @classmethod
    async def chat_completion(
        cls,
        system_instruction: str,
        messages: List[Dict[str, Any]],
        tools_spec: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Optional[Dict[str, Any]]:
        """
        Executes an OpenAI-compatible chat completion on Groq with native tool calling.

        Returns:
            Dict containing:
                - "content": str (if text response)
                - "tool_calls": List[Dict] (if model requested tool execution)
                - "raw": raw response dict
            Or None if Groq fails or is not configured.
        """
        if not cls.is_configured():
            logger.debug("Groq API key not configured, skipping Groq engine.")
            return None

        api_key = settings.GROQ_API_KEY.strip()
        model_name = cls.get_model()

        # Format messages for OpenAI format
        groq_messages = [{"role": "system", "content": system_instruction}]
        for m in messages:
            r = m.get("role", "user")
            c = m.get("content", "")
            # Map model -> assistant
            if r == "model":
                r = "assistant"
            groq_messages.append({"role": r, "content": str(c)})

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": groq_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Format tools for OpenAI function calling
        if tools_spec:
            groq_tools = []
            for t in tools_spec:
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": cls._normalize_schema(t.get("parameters", {"type": "object", "properties": {}}))
                    }
                })
            payload["tools"] = groq_tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AURA-Hospital-Copilot/1.0"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(cls.API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    msg_obj = choice.get("message", {})
                    
                    result = {
                        "content": msg_obj.get("content") or "",
                        "tool_calls": [],
                        "raw": data
                    }

                    # Parse tool calls if any
                    raw_tool_calls = msg_obj.get("tool_calls") or []
                    for tc in raw_tool_calls:
                        func_part = tc.get("function", {})
                        fname = func_part.get("name")
                        fargs_str = func_part.get("arguments", "{}")
                        try:
                            fargs = json.loads(fargs_str) if isinstance(fargs_str, str) else (fargs_str or {})
                        except Exception:
                            fargs = {}
                        if fname:
                            result["tool_calls"].append({
                                "id": tc.get("id"),
                                "name": fname,
                                "arguments": fargs
                            })

                    return result
                else:
                    logger.warning(f"Groq API returned HTTP {resp.status_code}: {resp.text[:200]}")
                    return None
        except Exception as e:
            logger.warning(f"Groq API call exception: {e}")
            return None
