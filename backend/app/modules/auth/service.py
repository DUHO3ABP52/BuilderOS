from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserRead


def ensure_first_user(session: Session) -> None:
    exists = session.scalar(select(User.id).limit(1))
    if exists:
        return
    session.add(
        User(
            email=settings.first_user_email,
            full_name=settings.first_user_name,
            hashed_password=hash_password(settings.first_user_password),
            role=UserRole.ADMIN,
        )
    )
    session.flush()


def authenticate_user(session: Session, payload: LoginRequest) -> User | None:
    user = session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        return None
    return user


def issue_token(user: User) -> TokenResponse:
    token = create_access_token(str(user.id), {"role": user.role})
    return TokenResponse(access_token=token)


def user_to_read(user: User) -> UserRead:
    return UserRead.model_validate(user)
