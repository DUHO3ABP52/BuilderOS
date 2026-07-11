from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.graph.service import build_project_graph, summarize_project_graph
from app.modules.projects.models import Project
from sqlalchemy import select


def resolve_project(session: Session, project_id: UUID | None = None, message: str = "") -> Project | None:
    if project_id is not None:
        project = session.get(Project, project_id)
        if project and not project.is_archived:
            return project
    text = message.lower()
    projects = list(session.scalars(select(Project).where(Project.is_archived.is_(False)).limit(50)))
    for project in projects:
        if project.name.lower() in text:
            return project
    return projects[0] if len(projects) == 1 else None


def project_context(session: Session, project_id: UUID | None = None, message: str = "") -> tuple[str, dict]:
    project = resolve_project(session, project_id=project_id, message=message)
    if project is None:
        return (
            "Не понял объект. Укажите project_id или название объекта в запросе "
            "(или создайте единственный объект в системе).",
            {},
        )
    graph = build_project_graph(session, project.id)
    if graph is None:
        return "Объект не найден.", {}
    return summarize_project_graph(graph), {
        "project_id": str(graph.project_id),
        "project_name": graph.project_name,
        "stats": graph.stats,
        "nodes": [node.model_dump(mode="json") for node in graph.nodes[:30]],
        "edges": [edge.model_dump(mode="json") for edge in graph.edges[:40]],
    }
