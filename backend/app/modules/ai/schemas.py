from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentName(StrEnum):
    COORDINATOR = "coordinator"
    DOCUMENT = "document"
    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    TASK = "task"


class IntentName(StrEnum):
    CREATE_DOCUMENT = "create_document"
    SEARCH_KNOWLEDGE = "search_knowledge"
    REMEMBER = "remember"
    RECALL = "recall"
    CREATE_TASK = "create_task"
    LIST_TASKS = "list_tasks"
    HELP = "help"
    UNKNOWN = "unknown"


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    project_id: UUID | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False


class AssistantAction(BaseModel):
    type: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    reply: str
    intent: IntentName
    agent: AgentName
    status: str = "ok"
    missing_fields: list[str] = Field(default_factory=list)
    actions: list[AssistantAction] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
