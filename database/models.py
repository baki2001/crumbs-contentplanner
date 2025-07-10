from sqlalchemy import Column, BigInteger, Integer, String, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    name = Column(Text)
    role = Column(String, default="user")
    activities_created = relationship("Activity", back_populates="creator")
    activity_signups = relationship("ActivityParticipant", back_populates="user")

class ActivityTemplate(Base):
    __tablename__ = "activity_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)
    slot_definition = Column(JSON)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("activity_templates.id"))
    activity_type = Column(String)
    scheduled_time = Column(TIMESTAMP)
    created_by = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    creator = relationship("User", back_populates="activities_created")
    participants = relationship("ActivityParticipant", back_populates="activity")

class ActivityParticipant(Base):
    __tablename__ = "activity_participants"
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    role = Column(String)
    status = Column(String, default="confirmed")

    user = relationship("User", back_populates="activity_signups")
    activity = relationship("Activity", back_populates="participants")