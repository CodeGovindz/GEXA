"""
GEXA Python SDK - Web Search API for AI Agents
"""

from gexa_py.client import Gexa
from gexa_py.async_client import AsyncGexa
from gexa_py.models import (
    SearchResult,
    SearchResponse,
    PageContent,
    ContentsResponse,
    FindSimilarResponse,
    AnswerResponse,
    Citation,
    CrawlResponse,
    CrawlStatusResponse,
    ResearchResponse,
    ResearchSource,
    ResearchSection,
)

__version__ = "0.1.0"
__all__ = [
    "Gexa",
    "AsyncGexa",
    "SearchResult",
    "SearchResponse",
    "PageContent",
    "ContentsResponse",
    "FindSimilarResponse",
    "AnswerResponse",
    "Citation",
    "CrawlResponse",
    "CrawlStatusResponse",
    "ResearchResponse",
    "ResearchSource",
    "ResearchSection",
]
