"""SQLAlchemy database models for session management."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Session(Base):
    """Bot session model."""

    __tablename__ = "sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    bot_username = Column(String(255), nullable=False)
    server_host = Column(String(255), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default="active")
    session_metadata = Column(JSONB, default=dict)

    # Relationships
    tasks = relationship("Task", back_populates="session", cascade="all, delete-orphan")
    learned_skills = relationship(
        "LearnedSkill", back_populates="session", cascade="all, delete-orphan"
    )
    bot_states = relationship(
        "BotStateHistory", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Session(id={self.session_id}, username={self.bot_username}, status={self.status})>"


class Task(Base):
    """Task execution model."""

    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)
    task_description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=True)
    evaluation = Column(JSONB, nullable=True)
    bot_state_before = Column(JSONB, nullable=True)
    bot_state_after = Column(JSONB, nullable=True)
    generated_code = Column(Text, nullable=True)
    execution_result = Column(JSONB, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="tasks")
    learned_skills = relationship(
        "LearnedSkill", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Task(id={self.task_id}, description={self.task_description[:30]}, status={self.status})>"


class LearnedSkill(Base):
    """Learned skill model."""

    __tablename__ = "learned_skills"

    skill_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.task_id"), nullable=True)
    skill_name = Column(String(255), nullable=False)
    skill_code = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="learned_skills")
    task = relationship("Task", back_populates="learned_skills")

    def __repr__(self):
        return f"<LearnedSkill(id={self.skill_id}, name={self.skill_name})>"


class BotStateHistory(Base):
    """Bot state history model."""

    __tablename__ = "bot_states"

    state_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    position = Column(JSONB, nullable=True)
    inventory = Column(JSONB, nullable=True)
    health = Column(Float, nullable=True)
    food = Column(Float, nullable=True)
    event_type = Column(String(100), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="bot_states")

    def __repr__(self):
        return f"<BotStateHistory(id={self.state_id}, event={self.event_type})>"
