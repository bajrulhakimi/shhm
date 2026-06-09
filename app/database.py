from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@retry(
    stop=stop_after_attempt(settings.external_request_max_attempts),
    wait=wait_exponential(multiplier=settings.external_request_backoff_seconds, max=30),
    reraise=True,
)
def init_db() -> None:
    from app.models import (  # noqa: F401
        analysis,
        scan_job,
        scan_result,
        stock,
        usage,
        user,
        watchlist,
    )

    Base.metadata.create_all(bind=engine)
