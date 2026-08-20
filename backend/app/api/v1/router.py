from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    comments,
    discussions,
    education,
    health,
    learning,
    lessons,
    pastpapers,
    practice,
    question_threads,
    quiz,
    teacher,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(education.router)
api_router.include_router(learning.router)
api_router.include_router(lessons.router)
api_router.include_router(practice.router)
api_router.include_router(quiz.router)
api_router.include_router(discussions.router)
api_router.include_router(comments.router)
api_router.include_router(question_threads.router)
api_router.include_router(teacher.router)
api_router.include_router(admin.router)
api_router.include_router(pastpapers.router)
