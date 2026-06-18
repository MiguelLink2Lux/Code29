"""Liveness endpoint. Dependency-free: no DB or external calls."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
