from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.blocks.models import DocumentBlock
from app.modules.blocks.schemas import BlockCreate, BlockRead
from app.modules.events.models import AuditAction
from app.modules.events.service import log_event

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.post("", response_model=BlockRead, status_code=status.HTTP_201_CREATED)
def create_block(
    payload: BlockCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentBlock:
    block = DocumentBlock(**payload.model_dump())
    session.add(block)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Блок с таким slug уже существует") from error
    log_event(
        session,
        actor_id=user.id,
        entity_type="block",
        entity_id=block.id,
        action=AuditAction.CREATE,
        summary=f"Создан блок {block.title}",
    )
    session.commit()
    session.refresh(block)
    return block


@router.get("", response_model=list[BlockRead])
def list_blocks(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DocumentBlock]:
    return list(
        session.scalars(
            select(DocumentBlock).where(DocumentBlock.is_archived.is_(False)).order_by(DocumentBlock.title)
        )
    )


@router.get("/{block_id}", response_model=BlockRead)
def get_block(
    block_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
) -> DocumentBlock:
    block = session.get(DocumentBlock, block_id)
    if block is None or block.is_archived:
        raise HTTPException(status_code=404, detail="Блок не найден")
    return block


@router.post("/{block_id}/archive", response_model=BlockRead)
def archive_block(
    block_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentBlock:
    block = session.get(DocumentBlock, block_id)
    if block is None or block.is_archived:
        raise HTTPException(status_code=404, detail="Блок не найден")
    block.is_archived = True
    log_event(
        session,
        actor_id=user.id,
        entity_type="block",
        entity_id=block.id,
        action=AuditAction.ARCHIVE,
        summary=f"Архивирован блок {block.title}",
    )
    session.commit()
    session.refresh(block)
    return block
