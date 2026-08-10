import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import request_id_context, hospital_id_context

class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Resolve request_id
        req_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        if not req_id:
            req_id = str(uuid.uuid4())[:8] # Keep request ID short for readable logging
        
        request_id_token = request_id_context.set(req_id)
        
        # 2. Resolve hospital_id
        hosp_id = request.headers.get("X-Hospital-ID") or request.headers.get("x-hospital-id")
        if not hosp_id:
            hosp_id = request.query_params.get("hospital_id")
        if not hosp_id:
            # Check path segments for patterns like HOSP-
            parts = request.url.path.strip("/").split("/")
            for p in parts:
                if p.startswith("HOSP-"):
                    hosp_id = p
                    break
        
        # Balaji Hospital fallback matching
        if not hosp_id and "balaji" in request.url.path.lower():
            hosp_id = "HOSP-BALA-7282"
            
        hospital_id_token = hospital_id_context.set(hosp_id)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_context.reset(request_id_token)
            hospital_id_context.reset(hospital_id_token)
