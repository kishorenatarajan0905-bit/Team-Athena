import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, ForeignKey, Index, UniqueConstraint,
    Enum as SQLEnum, Boolean, Integer, ARRAY
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, VECTOR
from app.core.database import Base
import enum


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MilestoneType(str, enum.Enum):
    FOUNDATION = "foundation"
    CORE = "core"
    SPECIALIZATION = "specialization"
    CAPSTONE = "capstone"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    profile: Mapped["LearnerProfile"] = relationship(back_populates="user", uselist=False)
    learning_paths: Mapped[List["LearningPath"]] = relationship(back_populates="user")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user")
    progress: Mapped[List["ProgressTracking"]] = relationship(back_populates="user")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    interests: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    experience_level: Mapped[ExperienceLevel] = mapped_column(SQLEnum(ExperienceLevel), default=ExperienceLevel.BEGINNER)
    goals: Mapped[str] = mapped_column(Text, default="")
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time_commitment_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    learning_style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_course_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), default=list)
    skill_embedding: Mapped[Optional[List[float]]] = mapped_column(VECTOR(3072), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="profile")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    difficulty: Mapped[ExperienceLevel] = mapped_column(SQLEnum(ExperienceLevel), default=ExperienceLevel.BEGINNER, index=True)
    duration_hours: Mapped[int] = mapped_column(Integer, default=0)
    prerequisites: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), default=list)
    skills_covered: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    embedding: Mapped[Optional[List[float]]] = mapped_column(VECTOR(3072), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    path_nodes: Mapped[List["PathNode"]] = relationship(back_populates="course")


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    estimated_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="learning_paths")
    nodes: Mapped[List["PathNode"]] = relationship(back_populates="path", order_by="PathNode.order_index")


class PathNode(Base):
    __tablename__ = "path_nodes"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    milestone_type: Mapped[MilestoneType] = mapped_column(SQLEnum(MilestoneType), default=MilestoneType.FOUNDATION)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    path: Mapped["LearningPath"] = relationship(back_populates="nodes")
    course: Mapped["Course"] = relationship(back_populates="path_nodes")

    __table_args__ = (
        Index("ix_path_nodes_path_order", "path_id", "order_index"),
        UniqueConstraint("path_id", "course_id", name="uq_path_course"),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    messages: Mapped[List[dict]] = mapped_column(default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="conversations")


class ProgressTracking(Base):
    __tablename__ = "progress_tracking"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    progress_pct: Mapped[float] = mapped_column(default=0.0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="progress")

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_course_progress"),
    )