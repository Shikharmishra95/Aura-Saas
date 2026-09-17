import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import request_id_context, correlation_id_context, hospital_id_context

class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Resolve request_id
        req_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        if not req_id:
            req_id = str(uuid.uuid4())[:8]
        
        request_id_token = request_id_context.set(req_id)

        # 2. Resolve correlation_id
        corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")
        if not corr_id:
            corr_id = req_id  # Fall back to request_id as root correlation ID
        
        correlation_id_token = correlation_id_context.set(corr_id)
        
        # 3. Resolve hospital_id
        hosp_id = request.headers.get("X-Hospital-ID") or request.headers.get("x-hospital-id")
        if not hosp_id:
            hosp_id = request.query_params.get("hospital_id")
        if not hosp_id:
            parts = request.url.path.strip("/").split("/")
            for p in parts:
                if p.startswith("HOSP-"):
                    hosp_id = p
                    break
        
        hospital_id_token = hospital_id_context.set(hosp_id)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            request_id_context.reset(request_id_token)
            correlation_id_context.reset(correlation_id_token)
            hospital_id_context.reset(hospital_id_token)

