from database.database import AsyncSessionLocal, get_db_session
from database.models import User
from sqlalchemy.future import select
from functools import wraps
from typing import Optional

async def is_admin(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        return user and user.role == "admin"

def with_permissions(role: Optional[str] = None, admin_override: bool = True):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = args[1] if len(args) > 1 else kwargs.get('ctx')
            if admin_override and await is_admin(ctx.author.id):
                return await func(*args, **kwargs)
            # Additional permission checks can be added here
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def admin_only():
    return with_permissions(admin_override=True)