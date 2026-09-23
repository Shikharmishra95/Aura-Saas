import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

# ─── Sentry Error Monitoring — AURA Backend ────────────────────────────────
# Captures ALL unhandled exceptions, slow DB queries, API performance traces.
# send_default_pii=False → Patient names, phones, OTPs are NEVER sent to Sentry .
# Docs: https://docs.sentry.io/platforms/python/integrations/fastapi/
if not os.getenv("DISABLE_SENTRY") and not os.getenv("PYTEST_CURRENT_TEST"):
    sentry_sdk.init(
        dsn="https://9c7474e970f0c976378ab5f0a547eb9b@o4512101179260928.ingest.us.sentry.io/4512101226446848",
        environment="production",        # Change to "development" locally
        release="aura-saas@1.0.0",      # Update version on each deploy
        send_default_pii=False,          # CRITICAL: Never send patient PII to Sentry
        enable_logs=True,                # Capture Python logger.error() calls too
        traces_sample_rate=0.2,          # Track 20% of requests for performance (free tier safe)
        profiles_sample_rate=0.1,        # Profile 10% of transactions
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",  # Groups traces by endpoint name
            ),
            SqlalchemyIntegration(),     # Captures slow/failed DB queries automatically
            LoggingIntegration(
                level=logging.ERROR,     # Send logger.error() and above to Sentry
                event_level=logging.ERROR,
            ),
        ],
    )
# ────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router
from app.core.logging import logger
from app.database.session import get_db

def create_app() -> FastAPI:
    """Application factory for configuring and returning the FastAPI app instance."""
    # Ensure all models are registered and compiled in SQLAlchemy metadata
    from app.database import base
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="Production API backend managing Twilio Voice and Gemini live connections for Hospital AI Receptionists.",
        version="1.0.0"
    )

    # 1. Register Global CORS Middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register Context Logging Middleware
    from app.core.middleware import LogContextMiddleware
    app.add_middleware(LogContextMiddleware)

    # 2. Register custom application exceptions mapping handlers
    register_exception_handlers(app)

    # 3. Import and include API routers with standard /api/v1 prefix
    from app.api.v1.router import api_router
    
    app.include_router(api_router, prefix=settings.API_V1_STR)


    # 4. Root Health Check Endpoint
    @app.get("/health", tags=["system"])
    async def health_check(db = Depends(get_db)):
        """Service status check — verifies database connectivity and AI service availability."""
        from sqlalchemy import text

        # 1. Database ping
        db_status = "healthy"
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_status = f"unhealthy: {str(e)}"

        # 2. Groq AI ping (lightweight — 1 token check)
        groq_status = "not_configured"
        try:
            from app.engines.groq_client import GroqClient
            if GroqClient.is_configured():
                result = await GroqClient.chat_completion(
                    system_instruction="ping",
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=1
                )
                groq_status = "healthy" if result is not None else "degraded"
        except Exception as e:
            logger.warning(f"Groq health check failed: {str(e)}")
            groq_status = "degraded"

        overall = "healthy" if db_status == "healthy" else "degraded"

        return {
            "status": overall,
            "database": db_status,
            "groq_ai": groq_status,
            "environment": settings.ENV,
            "project": settings.PROJECT_NAME
        }

    # 5. Serve React compiled frontend assets in production
    import os
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    # Resolve absolute path to frontend/dist
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dist = os.path.join(base_dir, "frontend", "dist")

    if os.path.exists(frontend_dist):
        assets_path = os.path.join(frontend_dist, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        # Catch-all endpoint for UI pages (directs to React SPA)
        @app.get("/{catchall:path}", include_in_schema=False)
        async def serve_react_app(catchall: str):
            index_path = os.path.join(frontend_dist, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"detail": "Frontend build files not found. Run npm run build."}

    logger.info("FastAPI application instance successfully created and configured.")
    return app

app = create_app()
