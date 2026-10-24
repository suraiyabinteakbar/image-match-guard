"""Database tables (SQLite via SQLAlchemy). See docs/design.md, section 6."""
import os
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint, create_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/app.db")


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String, unique=True)
    true_subject: Mapped[str | None] = mapped_column(String)
    subject: Mapped[str | None] = mapped_column(String)
    group_name: Mapped[str | None] = mapped_column(String, index=True)
    category: Mapped[str | None] = mapped_column(String)
    attributes: Mapped[list | None] = mapped_column(JSON)
    caption: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    caption_vector: Mapped[list | None] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    group_dict: Mapped[str | None] = mapped_column(String)
    group_llm: Mapped[str | None] = mapped_column(String)
    expected_group: Mapped[str | None] = mapped_column(String)
    group_note: Mapped[str | None] = mapped_column(Text)
    post_vector: Mapped[list | None] = mapped_column(JSON)


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = (
        UniqueConstraint("post_id", "image_id"),
        Index("ix_suggestions_post_id", "post_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"))
    similarity: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String)  # accepted / rejected
    reason: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String, default="pending")
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)


class CostLog(Base):
    __tablename__ = "cost_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String)  # vision / embedding / text
    model: Mapped[str] = mapped_column(String)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id"))
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String)  # ok / invalid / error
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


engine = create_engine(DB_URL)
SessionLocal = sessionmaker(engine)


def init_db():
    Base.metadata.create_all(engine)