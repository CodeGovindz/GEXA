"""
Synchronous GEXA client.
"""

from typing import Optional, List, Dict, Any

import httpx

from gexa_py.models import (
    SearchResponse,
    SearchFilters,
    ContentsResponse,
    FindSimilarResponse,
    AnswerResponse,
    CrawlResponse,
    CrawlStatusResponse,
    ResearchResponse,
    APIError,
)


class Gexa:
    """Synchronous GEXA API client.
    
    Example:
        >>> gexa = Gexa("your-api-key")
        >>> results = gexa.search("AI research papers")
        >>> print(results.results[0].title)
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,
    ):
        """Initialize the GEXA client.
        
        Args:
            api_key: Your GEXA API key
            base_url: API server URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=self.timeout,
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        response = self._client.request(method, endpoint, **kwargs)
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", str(error_data))
            except Exception:
                message = response.text
            raise APIError(response.status_code, message)
        
        return response.json()
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        include_content: bool = False,
        include_highlights: bool = False,
        filters: Optional[SearchFilters] = None,
    ) -> SearchResponse:
        """Perform semantic web search.
        
        Args:
            query: Search query
            num_results: Number of results (1-100)
            include_content: Include full page content
            include_highlights: Include relevant highlights
            filters: Optional search filters
            
        Returns:
            SearchResponse with results
        """
        payload = {
            "query": query,
            "num_results": num_results,
            "include_content": include_content,
            "include_highlights": include_highlights,
        }
        
        if filters:
            payload["filters"] = filters.model_dump(exclude_none=True)
        
        data = self._request("POST", "/search", json=payload)
        return SearchResponse(**data)
    
    def search_and_contents(
        self,
        query: str,
        num_results: int = 10,
        include_highlights: bool = True,
        filters: Optional[SearchFilters] = None,
    ) -> SearchResponse:
        """Search and include content in one call.
        
        Convenience method equivalent to search(..., include_content=True).
        """
        return self.search(
            query=query,
            num_results=num_results,
            include_content=True,
            include_highlights=include_highlights,
            filters=filters,
        )
    
    def get_contents(
        self,
        urls: List[str],
        include_markdown: bool = True,
        include_summary: bool = False,
        summary_max_length: int = 200,
    ) -> ContentsResponse:
        """Get content from URLs.
        
        Args:
            urls: List of URLs to fetch (max 10)
            include_markdown: Include markdown version
            include_summary: Generate AI summary
            summary_max_length: Max summary word count
            
        Returns:
            ContentsResponse with extracted content
        """
        payload = {
            "urls": urls,
            "include_markdown": include_markdown,
            "include_summary": include_summary,
            "summary_max_length": summary_max_length,
        }
        
        data = self._request("POST", "/contents", json=payload)
        return ContentsResponse(**data)
    
    def find_similar(
        self,
        url: str,
        num_results: int = 10,
        include_content: bool = False,
        exclude_source_domain: bool = True,
    ) -> FindSimilarResponse:
        """Find pages similar to a given URL.
        
        Args:
            url: Source URL
            num_results: Number of results
            include_content: Include page content
            exclude_source_domain: Exclude same domain
            
        Returns:
            FindSimilarResponse with similar pages
        """
        payload = {
            "url": url,
            "num_results": num_results,
            "include_content": include_content,
            "exclude_source_domain": exclude_source_domain,
        }
        
        data = self._request("POST", "/findsimilar", json=payload)
        return FindSimilarResponse(**data)
    
    def answer(
        self,
        query: str,
        num_sources: int = 5,
        include_citations: bool = True,
    ) -> AnswerResponse:
        """Get an AI-generated answer with citations.
        
        Args:
            query: Question to answer
            num_sources: Number of sources to use
            include_citations: Include source citations
            
        Returns:
            AnswerResponse with answer and citations
        """
        payload = {
            "query": query,
            "num_sources": num_sources,
            "include_citations": include_citations,
        }
        
        data = self._request("POST", "/answer", json=payload)
        return AnswerResponse(**data)
    
    def crawl(
        self,
        url: str,
        max_pages: int = 100,
        include_subdomains: bool = False,
    ) -> CrawlResponse:
        """Start a website crawl job.
        
        Args:
            url: Starting URL
            max_pages: Maximum pages to crawl
            include_subdomains: Include subdomains
            
        Returns:
            CrawlResponse with job ID
        """
        payload = {
            "url": url,
            "max_pages": max_pages,
            "include_subdomains": include_subdomains,
        }
        
        data = self._request("POST", "/crawl", json=payload)
        return CrawlResponse(**data)
    
    def get_crawl_status(self, job_id: str) -> CrawlStatusResponse:
        """Get the status of a crawl job.
        
        Args:
            job_id: Crawl job ID
            
        Returns:
            CrawlStatusResponse with status
        """
        data = self._request("GET", f"/crawl/status/{job_id}")
        return CrawlStatusResponse(**data)
