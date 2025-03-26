# app/routes/__init__.py
from fastapi import APIRouter
from app.routes import auth, financial

router = APIRouter()

# Include all route modules
router.include_router(auth.router)
router.include_router(financial.router)