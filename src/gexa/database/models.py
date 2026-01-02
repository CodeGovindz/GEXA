"""
SQLAlchemy database models for GEXA.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ApiKey(Base):
    """API key for authentication and rate limiting."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # For identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Supabase user ID
    
    # Quota and rate limiting
    quota_total: Mapped[int] = mapped_column(Integer, default=10000)
    quota_used: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    search_queries: Mapped[List["SearchQuery"]] = relationship(
        back_populates="api_key", cascade="all, delete-orphan"
    )
    crawl_jobs: Mapped[List["CrawlJob"]] = relationship(
        back_populates="api_key", cascade="all, delete-orphan"
    )


class WebPage(Base):
    """Crawled web page with extracted content."""

    __tablename__ = "web_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Content
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Raw text
    markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Markdown version
    
    # Metadata
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Technical
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    chunks: Mapped[List["PageChunk"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_web_pages_domain_crawled", "domain", "crawled_at"),
    )


class PageChunk(Base):
    """Text chunk with embedding for semantic search."""

    __tablename__ = "page_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("web_pages.id", ondelete="CASCADE"), nullable=False
    )
    
    # Content
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Embedding (768 dimensions for Gemini text-embedding-004)
    embedding = Column(Vector(768), nullable=True)
    
    # Metadata
    start_char: Mapped[int] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    page: Mapped["WebPage"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_page_chunks_page_id", "page_id"),
    )


class CrawlJob(Base):
    """Crawl job tracking."""

    __tablename__ = "crawl_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False
    )
    
    # Job details
    seed_url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    max_pages: Mapped[int] = mapped_column(Integer, default=100)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, running, completed, failed
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_indexed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    api_key: Mapped["ApiKey"] = relationship(back_populates="crawl_jobs")


class SearchQuery(Base):
    """Search query logging for analytics."""

    __tablename__ = "search_queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False
    )
    
    # Query details
    query: Mapped[str] = mapped_column(Text, nullable=False)
    num_results: Mapped[int] = mapped_column(Integer, default=10)
    filters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    # Results
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    api_key: Mapped["ApiKey"] = relationship(back_populates="search_queries")
