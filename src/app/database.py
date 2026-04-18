from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


engine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global engine, AsyncSessionLocal
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    assert AsyncSessionLocal is not None, "Database not initialized - call init_db() first"
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
