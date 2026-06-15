import os
import logging
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base

logger = logging.getLogger("backend.db.session")

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5435/financial_analyst"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db(): 
    async with async_session() as session: 
        try: 
            yield session
            await session.commit()
        except Exception as e: 
            logger.error(f"Database transaction error. Rolling back session: {str(e)}", exc_info=True)
            await session.rollback()
            raise
        finally: 
            await session.close()