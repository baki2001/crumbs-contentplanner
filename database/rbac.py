from config import ADMIN_IDS
from functools import wraps

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def admin_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            # Allow bot owner to bypass admin check
            if ctx.author.id == ctx.bot.owner_id:
                return await func(ctx, *args, **kwargs)
                
            if not is_admin(ctx.author.id):
                await ctx.send("❌ You are not authorized to use this command.", ephemeral=True)
                return
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator