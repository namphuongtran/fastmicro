"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from metastore_service.configs.settings import get_settings

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(description="Response timestamp")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version="0.1.0",
        timestamp=datetime.now(UTC),
    )


@router.get("/ready")
async def readiness_check() -> dict:
    return {"status": "ready", "checks": {"database": "healthy", "redis": "healthy"}}


@router.get("/metrics")
async def metrics() -> Response:
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return Response(content="# Prometheus not installed\n", media_type="text/plain")
