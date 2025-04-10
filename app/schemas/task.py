from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class TagBase(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)

class TagResponse(TagBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat() if dt else None
        }
    )

class TaskBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    priority: int = Field(default=3, ge=1, le=5)
    due_date: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TaskCreate(TaskBase):
    tags: List[str] = Field(default_factory=list)

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    owner_id: int
    tags: List[str] = []
    is_completed: bool = False
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat()
        }
    ) 