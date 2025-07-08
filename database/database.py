from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import DATABASE_URL
from database.models import Base
import logging

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    future=True
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("✅ Database initialized")

async def check_db_health():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logging.error(f"❌ Database health check failed: {e}")
        return False