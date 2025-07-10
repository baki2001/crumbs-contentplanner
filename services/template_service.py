import logging
from database.database import AsyncSessionLocal
from database.models import ActivityTemplate
from sqlalchemy.future import select
from services.user_service import UserService

class TemplateService:
    @staticmethod
    async def create_template(name: str, description: str, slot_definition: dict, creator_id: int, creator_name: str):
        async with AsyncSessionLocal() as session:
            # Ensure user exists
            creator = await UserService.get_or_create_user(creator_id, creator_name)
            
            template = ActivityTemplate(
                name=name,
                description=description,
                slot_definition=slot_definition,
                created_by=creator_id
            )
            session.add(template)
            await session.commit()
            return template
    
    @staticmethod
    async def get_all_templates():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ActivityTemplate))
            return result.scalars().all()
    
    @staticmethod
    async def get_template_by_name(name: str):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ActivityTemplate).where(ActivityTemplate.name == name)
            )
            return result.scalars().first()