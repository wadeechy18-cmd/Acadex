from fastapi import APIRouter

from app.api.v1.endpoints import auth, education, health, learning, lessons

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(education.router)
api_router.include_router(learning.router)
api_router.include_router(lessons.router)
