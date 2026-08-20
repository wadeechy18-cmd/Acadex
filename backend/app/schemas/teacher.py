from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserResponse


class StudentProgressRow(BaseModel):
    student: UserResponse
    completion_percentage: float
    enrolled_at: datetime
