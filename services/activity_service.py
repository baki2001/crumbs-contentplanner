import logging
from database.database import AsyncSessionLocal
from database.models import Activity, ActivityParticipant
from sqlalchemy.future import select
from sqlalchemy import delete, func
from services.user_service import UserService
from datetime import datetime

class ActivityService:
    @staticmethod
    async def create_activity(template_id: int, scheduled_time, location: str, creator_id: int, creator_name: str):
        async with AsyncSessionLocal() as session:
            # Ensure user exists
            creator = await UserService.get_or_create_user(creator_id, creator_name)
            
            activity = Activity(
                template_id=template_id,
                scheduled_time=scheduled_time,
                location=location,
                created_by=creator_id
            )
            session.add(activity)
            await session.commit()
            await session.refresh(activity)
            return activity

    @staticmethod
    async def get_activity_by_id(activity_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Activity).where(Activity.id == activity_id)
            )
            return result.scalars().first()
    
    @staticmethod
    async def get_all_upcoming_activities():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Activity).where(Activity.scheduled_time > datetime.utcnow())
            )
            return result.scalars().all()
    
    @staticmethod
    async def add_participant(activity_id: int, user_id: int, user_name: str, role: str):
        async with AsyncSessionLocal() as session:
            # Ensure user exists
            user = await UserService.get_or_create_user(user_id, user_name)
            
            # Check if already participating
            existing = await session.execute(
                select(ActivityParticipant).where(
                    ActivityParticipant.activity_id == activity_id,
                    ActivityParticipant.user_id == user_id
                )
            )
            if existing.scalars().first():
                return None, "Already participating"
            
            # Check role limits
            activity = await ActivityService.get_activity_by_id(activity_id)
            if activity:
                slot_def = activity.template.slot_definition.get(role, {})
                if not slot_def.get('unlimited', False):
                    # Count current participants in this role
                    count_result = await session.execute(
                        select(func.count(ActivityParticipant.id)).where(
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
                delete(ActivityParticipant).where(
                    ActivityParticipant.activity_id == activity_id,
                    ActivityParticipant.user_id == user_id
                ).returning(ActivityParticipant)
            )
            await session.commit()
            return result.scalars().first()
    
    @staticmethod
    async def update_activity_message(activity_id: int, channel_id: int, message_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Activity).where(Activity.id == activity_id)
            )
            activity = result.scalars().first()
            if activity:
                activity.channel_id = channel_id
                activity.message_id = message_id
                await session.commit()
                return True
            return False  # Fixed: removed extra parenthesis here