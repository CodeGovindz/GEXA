"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# ============= Search Schemas =============

class SearchFilters(BaseModel):
    """Filters for search queries."""
    
    domains: Optional[List[str]] = Field(
        default=None, description="Filter to specific domains"
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None, description="Exclude specific domains"
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Filter results after this date"
    )
    end_date: Optional[datetime] = Field(
        default=None, description="Filter results before this date"
    )
    language: Optional[str] = Field(
        default=None, description="Filter by language code (e.g., 'en')"
    )


class SearchRequest(BaseModel):
    """Request schema for /search endpoint."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    num_results: int = Field(
        default=10, ge=1, le=100, description="Number of results to return"
    )
    include_content: bool = Field(
        default=False, description="Include page content in results"
    )
    include_highlights: bool = Field(
        default=False, description="Include relevant highlights"
    )
    filters: Optional[SearchFilters] = Field(
        default=None, description="Optional search filters"
    )


class SearchResult(BaseModel):
    """Individual search result."""
    
    id: str = Field(..., description="Unique result ID")
    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(default=None, description="Page title")
    score: float = Field(..., description="Relevance score")
    published_date: Optional[datetime] = Field(default=None, description="Publication date")
    author: Optional[str] = Field(default=None, description="Author name")
    
    # Optional fields based on request
    snippet: Optional[str] = Field(default=None, description="Short snippet from search")
    content: Optional[str] = Field(default=None, description="Full page content")
    highlights: Optional[List[str]] = Field(default=None, description="Relevant highlights")


class SearchResponse(BaseModel):
    """Response schema for /search endpoint."""
    
    query: str = Field(..., description="Original query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    took_ms: int = Field(..., description="Query time in milliseconds")


# ============= Contents Schemas =============

class ContentsRequest(BaseModel):
    """Request schema for /contents endpoint."""
    
    urls: List[str] = Field(
        ..., 
        min_length=1, 
        max_length=10, 
        description="URLs to fetch content from"
    )
    include_markdown: bool = Field(
        default=True, description="Include markdown version"
    )
    include_summary: bool = Field(
        default=False, description="Include AI-generated summary"
    )
    summary_max_length: Optional[int] = Field(
        default=200, description="Maximum summary length in words"
    )


class PageContent(BaseModel):
    """Content extracted from a single page."""
    
    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(default=None, description="Page title")
    content: Optional[str] = Field(default=None, description="Plain text content")
    markdown: Optional[str] = Field(default=None, description="Markdown content")
    summary: Optional[str] = Field(default=None, description="AI-generated summary")
    author: Optional[str] = Field(default=None, description="Author")
    published_date: Optional[datetime] = Field(default=None, description="Publication date")
    status: str = Field(default="success", description="Fetch status")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ContentsResponse(BaseModel):
    """Response schema for /contents endpoint."""
    
    results: List[PageContent] = Field(..., description="Content for each URL")
    took_ms: int = Field(..., description="Total time in milliseconds")


# ============= Crawl Schemas =============

class CrawlRequest(BaseModel):
    """Request schema for /crawl endpoint."""
    
    url: str = Field(..., description="Starting URL to crawl")
    max_pages: int = Field(
        default=100, ge=1, le=1000, description="Maximum pages to crawl"
    )
    include_subdomains: bool = Field(
        default=False, description="Include subdomains in crawl"
    )


class CrawlResponse(BaseModel):
    """Response schema for /crawl endpoint."""
    
    job_id: str = Field(..., description="Crawl job ID")
    status: str = Field(..., description="Job status")
    seed_url: str = Field(..., description="Starting URL")
    max_pages: int = Field(..., description="Maximum pages to crawl")
    message: str = Field(..., description="Status message")


class CrawlStatusResponse(BaseModel):
    """Response for crawl job status check."""
    
    job_id: str = Field(..., description="Crawl job ID")
    status: str = Field(..., description="Job status")
    pages_crawled: int = Field(default=0, description="Pages crawled so far")
    pages_indexed: int = Field(default=0, description="Pages indexed so far")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


# ============= Find Similar Schemas =============

class FindSimilarRequest(BaseModel):
    """Request schema for /findsimilar endpoint."""
    
    url: str = Field(..., description="URL to find similar pages for")
    num_results: int = Field(
        default=10, ge=1, le=100, description="Number of results"
    )
    include_content: bool = Field(
        default=False, description="Include page content"
    )
    exclude_source_domain: bool = Field(
        default=True, description="Exclude pages from the same domain"
    )


class FindSimilarResponse(BaseModel):
    """Response schema for /findsimilar endpoint."""
    
    source_url: str = Field(..., description="Original URL")
    results: List[SearchResult] = Field(..., description="Similar pages")
    took_ms: int = Field(..., description="Query time in milliseconds")


# ============= Answer Schemas =============

class AnswerRequest(BaseModel):
    """Request schema for /answer endpoint."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Question to answer")
    num_sources: int = Field(
        default=5, ge=1, le=20, description="Number of sources to use"
    )
    include_citations: bool = Field(
        default=True, description="Include source citations"
    )


class Citation(BaseModel):
    """Citation for an answer."""
    
    url: str = Field(..., description="Source URL")
    title: Optional[str] = Field(default=None, description="Source title")
    snippet: str = Field(..., description="Relevant snippet from source")


class AnswerResponse(BaseModel):
    """Response schema for /answer endpoint."""
    
    query: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer")
    citations: List[Citation] = Field(default=[], description="Source citations")
    took_ms: int = Field(..., description="Total time in milliseconds")


# ============= API Key Schemas =============

class ApiKeyCreate(BaseModel):
    """Request to create a new API key."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Key name")
    owner_email: Optional[str] = Field(default=None, description="Owner email")
    quota_total: int = Field(default=10000, description="Total quota")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit")


class ApiKeyResponse(BaseModel):
    """Response containing API key details."""
    
    id: str = Field(..., description="Key ID")
    key: str = Field(..., description="API key (only shown once)")
    key_prefix: str = Field(..., description="Key prefix for identification")
    name: str = Field(..., description="Key name")
    quota_total: int = Field(..., description="Total quota")
    quota_used: int = Field(..., description="Quota used")
    rate_limit_per_minute: int = Field(..., description="Rate limit")
    created_at: datetime = Field(..., description="Creation time")


class ApiKeyInfo(BaseModel):
    """API key info without the actual key."""
    
    id: str = Field(..., description="Key ID")
    key_prefix: str = Field(..., description="Key prefix")
    name: str = Field(..., description="Key name")
    quota_total: int = Field(..., description="Total quota")
    quota_used: int = Field(..., description="Quota used")
    rate_limit_per_minute: int = Field(..., description="Rate limit")
    is_active: bool = Field(..., description="Whether key is active")
    created_at: datetime = Field(..., description="Creation time")
    last_used_at: Optional[datetime] = Field(default=None, description="Last used time")


# ============= Common Schemas =============

class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Server time")
