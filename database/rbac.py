from database.database import AsyncSessionLocal
from database.models import User
from sqlalchemy.future import select
from functools import wraps

async def is_admin(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        return user and user.role == "admin"

def admin_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if not await is_admin(ctx.author.id):
                await ctx.send("❌ You are not authorized to use this command.")
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator