from pydantic import BaseModel
from typing import Optional


class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy_cache"


class StepRequest(BaseModel):
    action_type: str
    target: Optional[str] = None