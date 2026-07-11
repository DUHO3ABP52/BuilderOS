from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BuilderSection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    section_type: str = "generic"
    content: str
    editable: bool = True


class VariableDefinition(BaseModel):
    key: str
    var_type: str = "string"
    required: bool = False
    label: str | None = None


class BuilderDocument(BaseModel):
    title: str
    doc_type: str
    version: int = 1
    sections: list[BuilderSection] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def section_by_type(self, section_type: str) -> BuilderSection | None:
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None
