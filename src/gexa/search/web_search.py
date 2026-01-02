"""
Real-time web search service using DuckDuckGo.

This module provides live internet search capabilities without requiring
an external API key.
"""

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from duckduckgo_search import DDGS


@dataclass
class WebSearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }


class WebSearchService:
    """
    Real-time web search service using DuckDuckGo.
    
    Provides live internet search without requiring an API key.
    For higher quality results, Tavily can be used as an alternative.
    """
    
    def __init__(self):
        """Initialize the web search service."""
        self.ddgs = DDGS()
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        region: str = "wt-wt",  # Worldwide
        safesearch: str = "moderate",
    ) -> List[WebSearchResult]:
        """
        Search the web in real-time using DuckDuckGo.
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return (default: 10)
            region: Region for search results (default: worldwide)
            safesearch: Safe search level: off, moderate, strict
            
        Returns:
            List of WebSearchResult objects with title, url, and snippet
        """
        try:
            # Run DuckDuckGo search in a thread pool since it's synchronous
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(self.ddgs.text(
                    query,
                    max_results=num_results,
                    region=region,
                    safesearch=safesearch,
                ))
            )
            
            # Convert to WebSearchResult objects
            search_results = []
            for r in results:
                search_results.append(WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", r.get("link", "")),
                    snippet=r.get("body", r.get("snippet", "")),
                ))
            
            return search_results
            
        except Exception as e:
            # Log error but return empty results rather than failing
            print(f"Web search error: {e}")
            return []
    
    async def news_search(
        self,
        query: str,
        num_results: int = 10,
        region: str = "wt-wt",
    ) -> List[WebSearchResult]:
        """
        Search for news articles in real-time.
        
        Args:
            query: Search query string
            num_results: Maximum number of results
            region: Region for search results
            
        Returns:
            List of WebSearchResult objects for news articles
        """
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(self.ddgs.news(
                    query,
                    max_results=num_results,
                    region=region,
                ))
            )
            
            search_results = []
            for r in results:
                search_results.append(WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", r.get("link", "")),
                    snippet=r.get("body", r.get("excerpt", "")),
                ))
            
            return search_results
            
        except Exception as e:
            print(f"News search error: {e}")
            return []
