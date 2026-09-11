import uuid

from pydantic import BaseModel, Field


class AIEnhanceRequest(BaseModel):
    instructions: str | None = Field(default=None, max_length=2000)
    resource_ids: list[uuid.UUID] = Field(default_factory=list)


class UsageSummaryResponse(BaseModel):
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_cents: int
