from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calendar.models import CalendarEvent
from app.modules.companies.models import Company
from app.modules.documents.models import Document
from app.modules.finance.models import Payment
from app.modules.graph.models import GraphEdge, GraphEntityType, GraphRelationType
from app.modules.graph.schemas import GraphEdgeCreate, GraphLink, GraphNode, ProjectGraph
from app.modules.memory.service import recall
from app.modules.projects.models import Project
from app.modules.tasks.models import Task


def _node_key(entity_type: str, entity_id: UUID | str) -> str:
    return f"{entity_type}:{entity_id}"


def create_edge(session: Session, payload: GraphEdgeCreate, user_id: UUID) -> GraphEdge:
    data = payload.model_dump(mode="json")
    edge = GraphEdge(**data, created_by_id=user_id)
    session.add(edge)
    session.flush()
    return edge


def list_manual_edges(session: Session, project_id: UUID) -> list[GraphEdge]:
    return list(
        session.scalars(
            select(GraphEdge)
            .where(GraphEdge.project_id == project_id, GraphEdge.is_archived.is_(False))
            .order_by(GraphEdge.created_at.desc())
        )
    )


def build_project_graph(session: Session, project_id: UUID) -> ProjectGraph | None:
    project = session.get(Project, project_id)
    if project is None or project.is_archived:
        return None

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphLink] = []

    def add_node(entity_type: str, entity_id: UUID, label: str, **meta) -> str:
        key = _node_key(entity_type, entity_id)
        if key not in nodes:
            nodes[key] = GraphNode(
                id=key,
                entity_type=entity_type,
                entity_id=entity_id,
                label=label,
                meta=meta,
            )
        return key

    root = add_node(
        GraphEntityType.PROJECT.value,
        project.id,
        project.name,
        address=project.address,
        status=project.status,
        contract_value=float(project.contract_value) if project.contract_value is not None else None,
    )

    if project.customer_id:
        company = session.get(Company, project.customer_id)
        if company and not company.is_archived:
            target = add_node(
                GraphEntityType.COMPANY.value,
                company.id,
                company.name,
                kind=company.kind,
                inn=company.inn,
            )
            edges.append(
                GraphLink(
                    from_id=root,
                    to_id=target,
                    relation=GraphRelationType.HAS_CUSTOMER.value,
                    source="derived",
                    label="Заказчик",
                )
            )

    if project.contractor_id:
        company = session.get(Company, project.contractor_id)
        if company and not company.is_archived:
            target = add_node(
                GraphEntityType.COMPANY.value,
                company.id,
                company.name,
                kind=company.kind,
                inn=company.inn,
            )
            edges.append(
                GraphLink(
                    from_id=root,
                    to_id=target,
                    relation=GraphRelationType.HAS_CONTRACTOR.value,
                    source="derived",
                    label="Подрядчик",
                )
            )

    documents = list(
        session.scalars(
            select(Document).where(Document.project_id == project.id, Document.is_archived.is_(False)).limit(50)
        )
    )
    for doc in documents:
        target = add_node(
            GraphEntityType.DOCUMENT.value,
            doc.id,
            doc.title,
            doc_type=doc.doc_type,
            status=doc.status,
        )
        edges.append(
            GraphLink(
                from_id=root,
                to_id=target,
                relation=GraphRelationType.HAS_DOCUMENT.value,
                source="derived",
            )
        )

    tasks = list(
        session.scalars(select(Task).where(Task.project_id == project.id, Task.is_archived.is_(False)).limit(50))
    )
    for task in tasks:
        target = add_node(GraphEntityType.TASK.value, task.id, task.title, status=task.status)
        edges.append(
            GraphLink(from_id=root, to_id=target, relation=GraphRelationType.HAS_TASK.value, source="derived")
        )

    payments = list(
        session.scalars(
            select(Payment).where(Payment.project_id == project.id, Payment.is_archived.is_(False)).limit(50)
        )
    )
    for payment in payments:
        target = add_node(
            GraphEntityType.PAYMENT.value,
            payment.id,
            payment.title,
            amount=float(payment.amount),
            status=payment.status,
            direction=payment.direction,
        )
        edges.append(
            GraphLink(from_id=root, to_id=target, relation=GraphRelationType.HAS_PAYMENT.value, source="derived")
        )

    events = list(
        session.scalars(
            select(CalendarEvent)
            .where(CalendarEvent.project_id == project.id, CalendarEvent.is_archived.is_(False))
            .limit(50)
        )
    )
    for event in events:
        target = add_node(
            GraphEntityType.EVENT.value,
            event.id,
            event.title,
            event_type=event.event_type,
            starts_at=event.starts_at.isoformat(),
        )
        edges.append(
            GraphLink(from_id=root, to_id=target, relation=GraphRelationType.HAS_EVENT.value, source="derived")
        )

    memories = recall(session, query=None, limit=30, project_id=project.id)
    for fact in memories:
        target = add_node(
            GraphEntityType.MEMORY.value,
            fact.id,
            fact.key,
            kind=fact.kind,
            content=fact.content[:200],
        )
        edges.append(
            GraphLink(from_id=root, to_id=target, relation=GraphRelationType.HAS_MEMORY.value, source="derived")
        )

    manual = list_manual_edges(session, project.id)
    for edge in manual:
        from_key = add_node(edge.from_type, edge.from_id, edge.label or f"{edge.from_type}:{str(edge.from_id)[:8]}")
        to_key = add_node(edge.to_type, edge.to_id, f"{edge.to_type}:{str(edge.to_id)[:8]}")
        edges.append(
            GraphLink(
                from_id=from_key,
                to_id=to_key,
                relation=edge.relation,
                source=edge.source or "manual",
                label=edge.label,
                edge_id=edge.id,
            )
        )

    stats = {
        "nodes": len(nodes),
        "edges": len(edges),
        "documents": len(documents),
        "tasks": len(tasks),
        "payments": len(payments),
        "events": len(events),
        "memory": len(memories),
        "manual_edges": len(manual),
    }
    return ProjectGraph(
        project_id=project.id,
        project_name=project.name,
        nodes=list(nodes.values()),
        edges=edges,
        stats=stats,
        memory=[
            {"id": str(item.id), "key": item.key, "kind": item.kind, "content": item.content}
            for item in memories
        ],
    )


def summarize_project_graph(graph: ProjectGraph) -> str:
    lines = [
        f"Контекст объекта «{graph.project_name}»:",
        f"• узлов: {graph.stats.get('nodes', 0)}, связей: {graph.stats.get('edges', 0)}",
        f"• документы: {graph.stats.get('documents', 0)}, задачи: {graph.stats.get('tasks', 0)}",
        f"• платежи: {graph.stats.get('payments', 0)}, события: {graph.stats.get('events', 0)}",
        f"• память: {graph.stats.get('memory', 0)}",
    ]
    companies = [n for n in graph.nodes if n.entity_type == GraphEntityType.COMPANY.value]
    if companies:
        lines.append("Контрагенты:")
        for node in companies[:8]:
            role = ""
            for edge in graph.edges:
                if edge.to_id == node.id and edge.relation in {
                    GraphRelationType.HAS_CUSTOMER.value,
                    GraphRelationType.HAS_CONTRACTOR.value,
                }:
                    role = f" ({edge.label or edge.relation})"
                    break
            lines.append(f"• {node.label}{role}")
    if graph.memory:
        lines.append("Память по объекту:")
        for item in graph.memory[:5]:
            lines.append(f"• [{item['kind']}] {item['content'][:120]}")
    return "\n".join(lines)
