import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL

async def test_db():
    try:
        engine = create_async_engine(DATABASE_URL, echo=True)
        async with engine.begin() as conn:
            print("Connected to PostgreSQL!")
    except Exception as e:
        print("DB connection failed:", e)

asyncio.run(test_db())
