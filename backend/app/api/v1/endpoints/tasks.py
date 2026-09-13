import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskStatusUpdateRequest, TaskUpdateRequest
from app.services import auth_service, task_service

school_tasks_router = APIRouter(prefix="/schools", tags=["tasks"])
my_tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])


def _to_response(db: Session, task: Task) -> TaskResponse:
    assignee = db.get(User, task.assigned_to_user_id)
    subject = db.get(Subject, task.subject_id) if task.subject_id else None
    class_ = db.get(Class, task.class_id) if task.class_id else None
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        assigned_to_user_id=task.assigned_to_user_id,
        assigned_to_name=auth_service.get_display_name(db, assignee),
        subject_id=task.subject_id,
        subject_name=subject.name if subject else None,
        class_id=task.class_id,
        class_name=class_.name if class_ else None,
        deadline=task.deadline,
        priority=task.priority,
        status=task.status,
        effective_status=task_service.effective_status(task),
        created_at=task.created_at,
    )


@school_tasks_router.post("/{school_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    school_id: uuid.UUID, payload: TaskCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TaskResponse:
    task = task_service.create_task(db, user, school_id, payload)
    return _to_response(db, task)


@school_tasks_router.get("/{school_id}/tasks", response_model=list[TaskResponse])
def list_school_tasks(school_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TaskResponse]:
    return [_to_response(db, t) for t in task_service.list_school_tasks(db, user, school_id)]


@school_tasks_router.patch("/{school_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    school_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = task_service.update_task(db, user, school_id, task_id, payload)
    return _to_response(db, task)


@school_tasks_router.delete("/{school_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(school_id: uuid.UUID, task_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    task_service.delete_task(db, user, school_id, task_id)


@my_tasks_router.get("/mine", response_model=list[TaskResponse])
def list_my_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TaskResponse]:
    return [_to_response(db, t) for t in task_service.list_my_tasks(db, user)]


@my_tasks_router.patch("/{task_id}/status", response_model=TaskResponse)
def update_my_task_status(
    task_id: uuid.UUID, payload: TaskStatusUpdateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TaskResponse:
    task = task_service.update_my_task_status(db, user, task_id, payload.status)
    return _to_response(db, task)
