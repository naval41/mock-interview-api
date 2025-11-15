from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging
from sqlalchemy import event

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.log_level == "DEBUG",
    future=True
)

# Set search_path to the schema from settings after connecting
@event.listens_for(engine.sync_engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    logger.info("Setting search path to %s", settings.db_schema)
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {settings.db_schema}")
    cursor.close()

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncSession:
    """FastAPI dependency for getting database session"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            logger.error(f"Database session error: {type(e).__name__}: {e}")
            logger.exception("Full exception stack trace:")
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """Regular async function for getting database session (for use in services)"""
    return async_session_maker()


async def create_db_and_tables():
    logger.info("Creating database tables")
    logger.info(f"Database URL: {settings.database_url}")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def close_db():
    await engine.dispose()