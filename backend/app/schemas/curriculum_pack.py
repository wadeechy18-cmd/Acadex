from pydantic import BaseModel

from app.models.planner_class import YearGroup


class CurriculumPackStatus(BaseModel):
    id: str
    display_name: str
    year_group: YearGroup
    already_imported: bool
