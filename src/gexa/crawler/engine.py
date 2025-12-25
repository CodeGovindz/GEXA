"""
Web crawler engine using Playwright.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Set
from urllib.parse import urlparse, urljoin

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from gexa.config import settings
from gexa.crawler.extractor import ContentExtractor, ExtractedContent


@dataclass
class CrawlResult:
    """Result from crawling a single URL."""
    
    url: str
    status_code: int
    content: Optional[ExtractedContent] = None
    error: Optional[str] = None
    crawled_at: datetime = None
    
    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = datetime.utcnow()


class CrawlerEngine:
    """Playwright-based web crawler with JavaScript rendering."""
    
    def __init__(
        self,
        max_concurrent: int = None,
        timeout: int = None,
        user_agent: str = None,
    ):
        self.max_concurrent = max_concurrent or settings.crawler_max_concurrent
        self.timeout = (timeout or settings.crawler_timeout) * 1000  # Convert to ms
        self.user_agent = user_agent or settings.crawler_user_agent
        self.extractor = ContentExtractor()
        
        self._browser: Optional[Browser] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def __aenter__(self):
        """Start browser on context enter."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close browser on context exit."""
        await self.close()
    
    async def start(self):
        """Start the browser instance."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ]
            )
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def close(self):
        """Close the browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
    
    async def crawl_url(self, url: str) -> CrawlResult:
        """Crawl a single URL and extract content.
        
        Args:
            url: URL to crawl
            
        Returns:
            CrawlResult with status and extracted content
        """
        if self._browser is None:
            await self.start()
        
        async with self._semaphore:
            page = await self._browser.new_page(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 720},
            )
            
            try:
                # Navigate to the page
                response = await page.goto(
                    url,
                    timeout=self.timeout,
                    wait_until="networkidle",
                )
                
                status_code = response.status if response else 0
                
                if status_code >= 400:
                    return CrawlResult(
                        url=url,
                        status_code=status_code,
                        error=f"HTTP {status_code}",
                    )
                
                # Wait for content to load
                await page.wait_for_load_state("domcontentloaded")
                
                # Get the HTML content
                html = await page.content()
                
                # Extract content
                content = self.extractor.extract(url, html)
                
                return CrawlResult(
                    url=url,
                    status_code=status_code,
                    content=content,
                )
                
            except PlaywrightTimeout:
                return CrawlResult(
                    url=url,
                    status_code=0,
                    error="Timeout while loading page",
                )
            except Exception as e:
                return CrawlResult(
                    url=url,
                    status_code=0,
                    error=str(e),
                )
            finally:
                await page.close()
    
    async def crawl_urls(self, urls: List[str]) -> List[CrawlResult]:
        """Crawl multiple URLs concurrently.
        
        Args:
            urls: List of URLs to crawl
            
        Returns:
            List of CrawlResult objects
        """
        tasks = [self.crawl_url(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def crawl_site(
        self,
        seed_url: str,
        max_pages: int = 100,
        include_subdomains: bool = False,
        callback=None,
    ) -> List[CrawlResult]:
        """Crawl an entire site starting from seed URL.
        
        Args:
            seed_url: Starting URL
            max_pages: Maximum pages to crawl
            include_subdomains: Whether to include subdomains
            callback: Optional callback for progress updates
            
        Returns:
            List of CrawlResult objects
        """
        if self._browser is None:
            await self.start()
        
        parsed_seed = urlparse(seed_url)
        base_domain = parsed_seed.netloc
        
        visited: Set[str] = set()
        to_visit: List[str] = [seed_url]
        results: List[CrawlResult] = []
        
        while to_visit and len(results) < max_pages:
            # Get next batch of URLs
            batch_size = min(self.max_concurrent, max_pages - len(results))
            batch = []
            
            while to_visit and len(batch) < batch_size:
                url = to_visit.pop(0)
                normalized = self._normalize_url(url)
                
                if normalized not in visited:
                    visited.add(normalized)
                    batch.append(url)
            
            if not batch:
                break
            
            # Crawl the batch
            batch_results = await self.crawl_urls(batch)
            
            for result in batch_results:
                results.append(result)
                
                # Extract links from successful crawls
                if result.content and result.content.links:
                    for link in result.content.links:
                        absolute_url = urljoin(result.url, link)
                        parsed = urlparse(absolute_url)
                        
                        # Check if link is within scope
                        if self._is_in_scope(parsed, base_domain, include_subdomains):
                            normalized = self._normalize_url(absolute_url)
                            if normalized not in visited:
                                to_visit.append(absolute_url)
                
                # Call progress callback
                if callback:
                    await callback(len(results), max_pages, result)
        
        return results
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Remove fragment and trailing slash
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.lower()
    
    def _is_in_scope(
        self,
        parsed_url,
        base_domain: str,
        include_subdomains: bool,
    ) -> bool:
        """Check if URL is within crawl scope."""
        if parsed_url.scheme not in ("http", "https"):
            return False
        
        if include_subdomains:
            return parsed_url.netloc.endswith(base_domain)
        else:
            return parsed_url.netloc == base_domain
    
    @staticmethod
    def get_content_hash(content: str) -> str:
        """Generate hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()
