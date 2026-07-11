from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.graph.models import GraphEntityType, GraphRelationType


class GraphEdgeCreate(BaseModel):
    project_id: UUID
    from_type: GraphEntityType
    from_id: UUID
    to_type: GraphEntityType
    to_id: UUID
    relation: GraphRelationType = GraphRelationType.RELATED_TO
    label: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="manual", max_length=32)


class GraphEdgeRead(BaseModel):
    id: UUID
    project_id: UUID
    from_type: str
    from_id: UUID
    to_type: str
    to_id: UUID
    relation: str
    label: str | None
    notes: str | None
    confidence: float
    source: str
    created_by_id: UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GraphNode(BaseModel):
    id: str
    entity_type: str
    entity_id: UUID | None = None
    label: str
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphLink(BaseModel):
    from_id: str
    to_id: str
    relation: str
    source: str
    label: str | None = None
    edge_id: UUID | None = None


class ProjectGraph(BaseModel):
    project_id: UUID
    project_name: str
    nodes: list[GraphNode]
    edges: list[GraphLink]
    stats: dict[str, int]
    memory: list[dict[str, Any]] = Field(default_factory=list)
