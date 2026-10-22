from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, tables, menu

api_router = APIRouter()
api_router.include_router(health.router, prefix="", tags=["System"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tables.router, prefix="/tables", tags=["Tables & QR Access"])
api_router.include_router(menu.router, prefix="", tags=["Digital Menu & Modifiers"])
