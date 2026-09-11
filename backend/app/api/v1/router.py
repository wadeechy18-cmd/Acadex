from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    ai,
    auth,
    classes,
    comments,
    discussions,
    education,
    health,
    homework,
    learning,
    lesson_plans,
    lessons,
    notifications,
    organizations,
    pastpapers,
    practice,
    question_threads,
    quiz,
    resources,
    search,
    teacher,
    weekly_plans,
    worksheets,
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
api_router.include_router(search.router)
api_router.include_router(notifications.router)
api_router.include_router(organizations.router)
api_router.include_router(classes.router)
api_router.include_router(lesson_plans.router)
api_router.include_router(resources.router)
api_router.include_router(worksheets.router)
api_router.include_router(homework.router)
api_router.include_router(weekly_plans.router)
api_router.include_router(ai.router)
