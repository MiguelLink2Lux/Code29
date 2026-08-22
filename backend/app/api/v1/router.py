"""Aggregate router for API v1. New v1 routers attach here (OCP)."""

from fastapi import APIRouter

from app.api.v1 import contact_report, health

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(health.router)
api_v1.include_router(contact_report.router)
