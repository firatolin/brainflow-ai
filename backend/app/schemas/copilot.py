from typing import Any
from pydantic import BaseModel, Field


class CopilotQuery(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class CopilotResponse(BaseModel):
    question: str
    answer: str
    source: str
    tool_used: str
    facts: dict[str, Any]
