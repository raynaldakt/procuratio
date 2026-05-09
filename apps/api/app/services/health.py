from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import redis

from app.core.config import get_settings


def check_database() -> tuple[bool, str]:
    settings = get_settings()
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, "ok"
    except SQLAlchemyError as exc:
        return False, str(exc)


def check_redis() -> tuple[bool, str]:
    settings = get_settings()
    try:
        client = redis.from_url(settings.redis_url)
        client.ping()
        return True, "ok"
    except redis.RedisError as exc:
        return False, str(exc)
