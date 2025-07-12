import logging
from database.database import AsyncSessionLocal
from database.models import Activity, ActivityParticipant, ActivityTemplate
from sqlalchemy.future import select
from sqlalchemy import delete, func
from sqlalchemy.orm import selectinload  # Added missing import
from services.user_service import UserService
from datetime import datetime

class ActivityService:
    @staticmethod
    async def create_activity(template_id: int, scheduled_time, location: str, creator_id: int, creator_name: str):
        async with AsyncSessionLocal() as session:
            # Ensure user exists
            creator = await UserService.get_or_create_user(creator_id, creator_name)
            
            # Get template with the same session
            template = await session.get(ActivityTemplate, template_id)
            if not template:
                raise ValueError(f"Template with ID {template_id} not found")

            # Create activity with explicit template relationship
            activity = Activity(
                template_id=template_id,
                scheduled_time=scheduled_time,
                location=location,
                created_by=creator_id,
                template=template  # Manually set the relationship
            )
            
            session.add(activity)
            await session.commit()
            await session.refresh(activity)
            
            # Return a fresh instance with all relationships loaded
            return await session.get(Activity, activity.id, options=[selectinload(Activity.template)])

    @staticmethod
    async def get_activity_by_id(activity_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Activity)
                .where(Activity.id == activity_id)
                .options(selectinload(Activity.template))  # Fixed syntax
            )
            return result.scalars().first()
    
    @staticmethod
    async def get_all_upcoming_activities():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Activity)
                .where(Activity.scheduled_time > datetime.utcnow())
                .options(selectinload(Activity.template))  # Fixed syntax
            )
            return result.scalars().all()
    
    @staticmethod
    async def add_participant(activity_id: int, user_id: int, user_name: str, role: str):
        async with AsyncSessionLocal() as session:
            # Ensure user exists
            user = await UserService.get_or_create_user(user_id, user_name)
            
            # Get activity with template preloaded
            result = await session.execute(
                select(Activity)
                .where(Activity.id == activity_id)
                .options(selectinload(Activity.template))  # Fixed syntax
            )
            activity = result.scalars().first()
            
            if not activity:
                return None, "Activity not found"
            
            # Check if already participating
            existing = await session.execute(
                select(ActivityParticipant)
                .where(
                    ActivityParticipant.activity_id == activity_id,
                    ActivityParticipant.user_id == user_id
                )
            )
            if existing.scalars().first():
                return None, "Already participating"
            
            # Check role limits
            slot_def = activity.template.slot_definition.get(role, {})
            if not slot_def.get('unlimited', False):
                count_result = await session.execute(
                    select(func.count(ActivityParticipant.id))
                    .where(
                        ActivityParticipant.activity_id == activity_id,
                        ActivityParticipant.role == role
                    )
                )
                current_count = count_result.scalar()
                max_count = slot_def.get('count', 0)
                
                if current_count >= max_count:
                    return None, "Role is full"
            
            participant = ActivityParticipant(
                activity_id=activity_id,
                user_id=user_id,
                role=role
            )
            session.add(participant)
            await session.commit()
            await session.refresh(participant)
            return participant, None
    
    @staticmethod
    async def remove_participant(activity_id: int, user_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(ActivityParticipant)
                .where(
                    ActivityParticipant.activity_id == activity_id,
                    ActivityParticipant.user_id == user_id
                )
                .returning(ActivityParticipant)
            )
            await session.commit()
            return result.scalars().first()
    
    @staticmethod
    async def update_activity_message(activity_id: int, channel_id: int, message_id: int):
        async with AsyncSessionLocal() as session:
            activity = await session.get(Activity, activity_id)
            if activity:
                activity.channel_id = channel_id
                activity.message_id = message_id
                await session.commit()
                return True
            return False