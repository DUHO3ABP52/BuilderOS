from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event
from app.modules.graph.models import GraphEdge
from app.modules.graph.schemas import GraphEdgeCreate, GraphEdgeRead, ProjectGraph
from app.modules.graph.service import build_project_graph, create_edge, list_manual_edges
from app.modules.projects.models import Project

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/projects/{project_id}", response_model=ProjectGraph)
def get_project_graph(
    project_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> ProjectGraph:
    graph = build_project_graph(session, project_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Объект не найден")
    return graph


@router.get("/projects/{project_id}/edges", response_model=list[GraphEdgeRead])
def list_project_edges(
    project_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[GraphEdge]:
    project = session.get(Project, project_id)
    if project is None or project.is_archived:
        raise HTTPException(status_code=404, detail="Объект не найден")
    return list_manual_edges(session, project_id)


@router.post("/edges", response_model=GraphEdgeRead, status_code=status.HTTP_201_CREATED)
def create_graph_edge(
    payload: GraphEdgeCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GraphEdge:
    project = session.get(Project, payload.project_id)
    if project is None or project.is_archived:
        raise HTTPException(status_code=404, detail="Объект не найден")
    edge = create_edge(session, payload, user.id)
    log_event(
        session,
        actor_id=user.id,
        entity_type="graph_edge",
        entity_id=edge.id,
        action=AuditAction.CREATE,
        summary=f"Связь графа: {edge.relation} ({project.name})",
    )
    session.commit()
    session.refresh(edge)
    return edge


@router.post("/edges/{edge_id}/archive", response_model=GraphEdgeRead)
def archive_graph_edge(
    edge_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GraphEdge:
    edge = session.get(GraphEdge, edge_id)
    if edge is None or edge.is_archived:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    edge.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="graph_edge",
        entity_id=edge.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирована связь графа: {edge.relation}",
    )
    session.commit()
    session.refresh(edge)
    return edge
