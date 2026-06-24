"""System / health endpoints (PLAN.md Section 8)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check for Docker/deployment."""
    return HealthResponse(status="ok")
