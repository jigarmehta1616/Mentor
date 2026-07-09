"""SQLAlchemy ORM models mirroring db/schema.sql."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    explain_level: Mapped[str] = mapped_column(String, default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)


class ConceptEdge(Base):
    """Directed prerequisite edge: prereq_id must be learned before concept_id."""

    __tablename__ = "concept_edges"

    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
    prereq_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)


class Mastery(Base):
    __tablename__ = "mastery"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
    easiness_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    next_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0)
    last_score: Mapped[int | None] = mapped_column(Integer)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String)
    concept_id: Mapped[str | None] = mapped_column(String)
    question: Mapped[str | None] = mapped_column(Text)
    user_answer: Mapped[str | None] = mapped_column(Text)
    quality_score: Mapped[int | None] = mapped_column(Integer)
    misconception: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(String, index=True)
    role: Mapped[str | None] = mapped_column(String)
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    explain_level: Mapped[str] = mapped_column(String, default="student")
    path: Mapped[list[str]] = mapped_column(JSONB, default=list)
    current_concept: Mapped[str | None] = mapped_column(String)
    running_summary: Mapped[str] = mapped_column(Text, default="")
    phase: Mapped[str] = mapped_column(String, default="teach")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
