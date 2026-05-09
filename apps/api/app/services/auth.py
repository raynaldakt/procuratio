from threading import Lock

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.db.base import Base
from app.db.session import engine
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenPair, UserCreate

_schema_lock = Lock()
_schema_ready = False


def ensure_auth_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(bind=engine, tables=[User.__table__], checkfirst=True)
        _schema_ready = True


def get_user_by_email(db: Session, email: str) -> User | None:
    ensure_auth_schema()
    return db.scalar(select(User).where(User.email == email.lower().strip()))


def create_user(db: Session, payload: UserCreate) -> User:
    ensure_auth_schema()
    new_user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("A user with this email already exists") from exc

    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, payload: LoginRequest) -> User | None:
    user = get_user_by_email(db, payload.email)
    if user is None:
        return None

    if not verify_password(payload.password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user


def issue_tokens_for_user(user: User) -> TokenPair:
    subject = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )
