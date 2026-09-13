from fastapi import APIRouter

from app.api.v1.endpoints import auth, curriculum, health, lesson_plans, resources, schools

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(schools.router)
api_router.include_router(curriculum.router)
api_router.include_router(resources.router)
api_router.include_router(lesson_plans.router)
