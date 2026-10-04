import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Uuid


class Base(DeclarativeBase):
    pass


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_material_id_difficulty", "material_id", "difficulty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id"), nullable=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserAnswer(Base):
    __tablename__ = "user_answers"
    __table_args__ = (
        Index("ix_user_answers_user_id_answered_at", "user_id", "answered_at"),
        Index(
            "ix_user_answers_user_id_question_id_answered_at",
            "user_id",
            "question_id",
            "answered_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id"), nullable=False
    )
    selected_answer: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        Index("ix_study_sessions_material_id", "material_id"),
        Index("ix_study_sessions_started_at", "started_at"),
        Index("ix_study_sessions_user_id_started_at", "user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id"), nullable=False
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    correct_answers: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    accuracy: Mapped[float] = mapped_column(
        nullable=False, default=0.0
    )


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    items = relationship(
        "LearningPlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class LearningPlanItem(Base):
    __tablename__ = "learning_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    learning_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_plans.id"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    accuracy_snapshot: Mapped[float | None] = mapped_column(
        nullable=True
    )
    total_answers_snapshot: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    plan = relationship(
        "LearningPlan",
        back_populates="items",
    )
