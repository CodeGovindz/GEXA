"""
Pydantic models for GEXA SDK responses.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Filters for search queries."""
    
    domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    language: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result."""
    
    id: str
    url: str
    title: Optional[str] = None
    score: float
    published_date: Optional[datetime] = None
    author: Optional[str] = None
    content: Optional[str] = None
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Response from search endpoint."""
    
    query: str
    results: List[SearchResult]
    total_results: int
    took_ms: int


class PageContent(BaseModel):
    """Extracted content from a page."""
    
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    markdown: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    status: str = "success"
    error: Optional[str] = None


class ContentsResponse(BaseModel):
    """Response from contents endpoint."""
    
    results: List[PageContent]
    took_ms: int


class FindSimilarResponse(BaseModel):
    """Response from find_similar endpoint."""
    
    source_url: str
    results: List[SearchResult]
    took_ms: int


class Citation(BaseModel):
    """Citation in an answer."""
    
    url: str
    title: Optional[str] = None
    snippet: str


class AnswerResponse(BaseModel):
    """Response from answer endpoint."""
    
    query: str
    answer: str
    citations: List[Citation] = []
    took_ms: int


class CrawlResponse(BaseModel):
    """Response when starting a crawl job."""
    
    job_id: str
    status: str
    seed_url: str
    max_pages: int
    message: str


class CrawlStatusResponse(BaseModel):
    """Response for crawl job status."""
    
    job_id: str
    status: str
    pages_crawled: int = 0
    pages_indexed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class APIError(Exception):
    """Exception raised for API errors."""
    
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"API Error {status_code}: {message}")


# Research models
class ResearchSource(BaseModel):
    """Source used in research."""
    
    url: str
    title: Optional[str] = None
    relevance_score: float
    key_points: List[str] = []


class ResearchSection(BaseModel):
    """Section of a research report."""
    
    heading: str
    content: str
    sources: List[int] = []


class ResearchResponse(BaseModel):
    """Response from research endpoint."""
    
    topic: str
    summary: str
    sections: List[ResearchSection] = []
    sources: List[ResearchSource] = []
    methodology: str
    took_ms: int
