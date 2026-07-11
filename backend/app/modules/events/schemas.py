from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.events.models import AuditAction


class AuditEventRead(BaseModel):
    id: UUID
    actor_id: UUID | None
    entity_type: str
    entity_id: UUID | None
    action: AuditAction
    summary: str
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
