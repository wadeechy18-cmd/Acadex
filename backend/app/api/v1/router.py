from fastapi import APIRouter

from app.api.v1.endpoints import auth, classes, curriculum, health, lesson_plans, resources, schools, tasks, timetable

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(schools.router)
api_router.include_router(curriculum.router)
api_router.include_router(resources.router)
api_router.include_router(lesson_plans.router)
api_router.include_router(lesson_plans.school_lesson_plans_router)
api_router.include_router(classes.router)
api_router.include_router(classes.school_classes_router)
api_router.include_router(tasks.school_tasks_router)
api_router.include_router(tasks.my_tasks_router)
api_router.include_router(timetable.router)
