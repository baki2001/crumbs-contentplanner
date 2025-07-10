import logging
from database.database import AsyncSessionLocal
from database.models import User
from sqlalchemy.future import select
from sqlalchemy import insert

class UserService:
    @staticmethod
    async def get_or_create_user(user_id: int, user_name: str):
        async with AsyncSessionLocal() as session:
            # Check if user exists
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            
            if user:
                return user
                
            # Create new user if not exists
            new_user = User(id=user_id, name=user_name)
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            logging.info(f"Created new user: {user_id} - {user_name}")
            return new_user