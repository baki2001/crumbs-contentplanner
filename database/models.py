from sqlalchemy import Column, BigInteger, Integer, String, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    name = Column(Text)
    role = Column(String, default="user")  # user, admin
    raids_created = relationship("Raid", back_populates="creator")
    signups = relationship("Participant", back_populates="user")

class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    dungeon_type = Column(String)
    slots = Column(JSON)  # e.g. {"tank": 1, "healer": 2, "dps": 4}
    created_by = Column(BigInteger, ForeignKey("users.id"))

class Raid(Base):
    __tablename__ = "raids"
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    scheduled_time = Column(TIMESTAMP)
    created_by = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    creator = relationship("User", back_populates="raids_created")
    participants = relationship("Participant", back_populates="raid")

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True)
    raid_id = Column(Integer, ForeignKey("raids.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    role = Column(String)

    user = relationship("User", back_populates="signups")
    raid = relationship("Raid", back_populates="participants")