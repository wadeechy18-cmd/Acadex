import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.models.curriculum import Subject
from app.models.school import SchoolMembershipRole
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreateRequest, TaskUpdateRequest
from app.services import school_service


def effective_status(task: Task) -> str:
    if task.status != TaskStatus.COMPLETED and task.deadline < date.today():
        return "overdue"
    return task.status.value


def _validate_refs(db: Session, school_id: uuid.UUID, assigned_to_user_id: uuid.UUID, subject_id: uuid.UUID | None, class_id: uuid.UUID | None) -> None:
    assignee = db.get(User, assigned_to_user_id)
    if not assignee or not school_service.get_membership(db, assignee, school_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The assigned teacher must be a member of this school.")
    if subject_id and not db.get(Subject, subject_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found.")
    if class_id and not db.get(Class, class_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found.")


def create_task(db: Session, actor: User, school_id: uuid.UUID, payload: TaskCreateRequest) -> Task:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    _validate_refs(db, school_id, payload.assigned_to_user_id, payload.subject_id, payload.class_id)

    task = Task(
        school_id=school_id,
        created_by_user_id=actor.id,
        assigned_to_user_id=payload.assigned_to_user_id,
        title=payload.title,
        description=payload.description,
        subject_id=payload.subject_id,
        class_id=payload.class_id,
        deadline=payload.deadline,
        priority=payload.priority,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_school_tasks(db: Session, actor: User, school_id: uuid.UUID) -> list[Task]:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    return db.query(Task).filter_by(school_id=school_id).order_by(Task.deadline).all()


def list_my_tasks(db: Session, user: User) -> list[Task]:
    return db.query(Task).filter_by(assigned_to_user_id=user.id).order_by(Task.deadline).all()


def get_school_task(db: Session, actor: User, school_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    school_service.assert_school_member(db, actor, school_id, min_role=SchoolMembershipRole.ADMIN)
    task = db.query(Task).filter_by(id=task_id, school_id=school_id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    return task


def update_task(db: Session, actor: User, school_id: uuid.UUID, task_id: uuid.UUID, payload: TaskUpdateRequest) -> Task:
    task = get_school_task(db, actor, school_id, task_id)
    _validate_refs(db, school_id, payload.assigned_to_user_id, payload.subject_id, payload.class_id)

    task.title = payload.title
    task.description = payload.description
    task.assigned_to_user_id = payload.assigned_to_user_id
    task.subject_id = payload.subject_id
    task.class_id = payload.class_id
    task.deadline = payload.deadline
    task.priority = payload.priority
    task.status = payload.status
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, actor: User, school_id: uuid.UUID, task_id: uuid.UUID) -> None:
    task = get_school_task(db, actor, school_id, task_id)
    db.delete(task)
    db.commit()


def update_my_task_status(db: Session, user: User, task_id: uuid.UUID, new_status: TaskStatus) -> Task:
    task = db.query(Task).filter_by(id=task_id, assigned_to_user_id=user.id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    task.status = new_status
    db.commit()
    db.refresh(task)
    return task
