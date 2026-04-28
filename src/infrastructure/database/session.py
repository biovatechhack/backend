from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config.settings import settings


def create_engine() -> AsyncEngine:
    """Build the shared async SQLAlchemy engine."""
    return create_async_engine(settings.SQLITE_URL, future=True)


engine = create_engine()
SessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
