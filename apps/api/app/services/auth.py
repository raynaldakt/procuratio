from hashlib import sha256
from threading import Lock

from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from app.db.session import engine
from app.models.user_refresh_token import UserRefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserCreate

_schema_lock = Lock()
_schema_ready = False


def ensure_auth_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(bind=engine, tables=[User.__table__, UserRefreshToken.__table__], checkfirst=True)
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
        role="customer",
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


def _hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def issue_tokens_for_user(db: Session, user: User) -> TokenPair:
    ensure_auth_schema()
    subject = str(user.id)
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)
    token_hash = _hash_refresh_token(refresh_token)

    token_row = db.get(UserRefreshToken, user.id)
    if token_row is None:
        token_row = UserRefreshToken(user_id=user.id, token_hash=token_hash)
        db.add(token_row)
    else:
        token_row.token_hash = token_hash
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def refresh_user_tokens(db: Session, payload: RefreshRequest) -> TokenPair | None:
    ensure_auth_schema()
    try:
        decoded = decode_refresh_token(payload.refresh_token)
    except InvalidTokenError:
        return None

    token_type = decoded.get("type")
    subject = decoded.get("sub")
    if token_type != "refresh" or subject is None:
        return None

    user = db.get(User, int(subject))
    if user is None or not user.is_active:
        return None

    token_row = db.get(UserRefreshToken, user.id)
    if token_row is None:
        return None

    if token_row.token_hash != _hash_refresh_token(payload.refresh_token):
        return None

    return issue_tokens_for_user(db, user)


def logout_user(db: Session, user: User) -> None:
    ensure_auth_schema()
    token_row = db.get(UserRefreshToken, user.id)
    if token_row is not None:
        db.delete(token_row)
        db.commit()
