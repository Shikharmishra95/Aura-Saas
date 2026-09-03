from fastapi import APIRouter
from app.api.v1.endpoints.owner import overview, hospitals, observability, health

owner_router = APIRouter()

owner_router.include_router(overview.router, tags=["owner_overview"])
owner_router.include_router(hospitals.router, tags=["owner_hospitals"])
owner_router.include_router(observability.router, tags=["owner_observability"])
owner_router.include_router(health.router, tags=["owner_health"])
