"""Configuración de base de datos relacional para el historial de conversaciones."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()

if settings.database_url:
    db_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://")
else:
    db_url = f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesiones de base de datos para usar como dependencia en FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Crea todas las tablas definidas en los modelos declarativos."""
    import app.models.domain  # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


DBDependency = Annotated[AsyncSession, Depends(get_db)]

