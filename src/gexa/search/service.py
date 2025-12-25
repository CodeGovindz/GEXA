"""
Search service combining crawling, embedding, and vector search.
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.config import settings
from gexa.database.models import WebPage, PageChunk, SearchQuery, ApiKey
from gexa.crawler import CrawlerEngine, ContentExtractor
from gexa.search.embeddings import EmbeddingService
from gexa.search.vector_store import VectorStore


class SearchService:
    """High-level search service combining all components."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(db)
        self.extractor = ContentExtractor()
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        include_content: bool = False,
        include_highlights: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        api_key: Optional[ApiKey] = None,
    ) -> Dict[str, Any]:
        """Perform semantic search across indexed pages.
        
        Args:
            query: Search query
            num_results: Number of results to return
            include_content: Include full page content
            include_highlights: Include relevant highlights
            filters: Optional search filters
            api_key: API key for logging
            
        Returns:
            Search response with results
        """
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)
        
        # Convert filter schema to dict if needed
        filter_dict = None
        if filters:
            filter_dict = {
                "domains": filters.domains if hasattr(filters, 'domains') else filters.get("domains"),
                "exclude_domains": filters.exclude_domains if hasattr(filters, 'exclude_domains') else filters.get("exclude_domains"),
                "start_date": filters.start_date if hasattr(filters, 'start_date') else filters.get("start_date"),
                "end_date": filters.end_date if hasattr(filters, 'end_date') else filters.get("end_date"),
                "language": filters.language if hasattr(filters, 'language') else filters.get("language"),
            }
            # Remove None values
            filter_dict = {k: v for k, v in filter_dict.items() if v is not None}
        
        # Search vector store
        raw_results = await self.vector_store.search(
            query_embedding=query_embedding,
            limit=num_results,
            filters=filter_dict,
        )
        
        # Format results
        results = []
        for r in raw_results:
            result = {
                "id": r["page_id"],
                "url": r["url"],
                "title": r["title"],
                "score": r["score"],
                "published_date": r["published_date"],
                "author": r["author"],
            }
            
            if include_content:
                result["content"] = r["content"]
            
            if include_highlights and r.get("content"):
                result["highlights"] = self.extractor.get_highlights(
                    r["content"], query
                )
            
            results.append(result)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Log the query
        if api_key:
            search_log = SearchQuery(
                api_key_id=api_key.id,
                query=query,
                num_results=num_results,
                filters=str(filter_dict) if filter_dict else None,
                results_count=len(results),
                latency_ms=elapsed_ms,
            )
            self.db.add(search_log)
            await self.db.commit()
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "took_ms": elapsed_ms,
        }
    
    async def get_contents(
        self,
        urls: List[str],
        include_markdown: bool = True,
        include_summary: bool = False,
        summary_max_length: int = 200,
    ) -> Dict[str, Any]:
        """Get content from URLs, crawling if necessary.
        
        Args:
            urls: URLs to get content from
            include_markdown: Include markdown version
            include_summary: Generate AI summary
            summary_max_length: Max summary length
            
        Returns:
            Contents response
        """
        start_time = time.time()
        results = []
        
        async with CrawlerEngine() as crawler:
            for url in urls:
                # Check if we already have this page
                page = await self.vector_store.get_page_by_url(url)
                
                if page:
                    # Return cached content
                    result = {
                        "url": url,
                        "title": page.title,
                        "content": page.content,
                        "markdown": page.markdown if include_markdown else None,
                        "author": page.author,
                        "published_date": page.published_date,
                        "status": "success",
                    }
                else:
                    # Crawl the URL
                    crawl_result = await crawler.crawl_url(url)
                    
                    if crawl_result.error:
                        result = {
                            "url": url,
                            "status": "error",
                            "error": crawl_result.error,
                        }
                    else:
                        content = crawl_result.content
                        
                        # Save to database
                        page = await self._save_page(url, content)
                        
                        result = {
                            "url": url,
                            "title": content.title if content else None,
                            "content": content.content if content else None,
                            "markdown": content.markdown if content and include_markdown else None,
                            "author": content.author if content else None,
                            "published_date": content.published_date if content else None,
                            "status": "success",
                        }
                
                # Generate summary if requested
                if include_summary and result.get("status") == "success" and result.get("content"):
                    result["summary"] = await self._generate_summary(
                        result["content"], summary_max_length
                    )
                
                results.append(result)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return {
            "results": results,
            "took_ms": elapsed_ms,
        }
    
    async def find_similar(
        self,
        url: str,
        num_results: int = 10,
        include_content: bool = False,
        exclude_source_domain: bool = True,
    ) -> Dict[str, Any]:
        """Find pages similar to a given URL.
        
        Args:
            url: Source URL
            num_results: Number of results
            include_content: Include page content
            exclude_source_domain: Exclude same domain
            
        Returns:
            Similar pages response
        """
        start_time = time.time()
        
        # Get or crawl the source page
        page = await self.vector_store.get_page_by_url(url)
        
        if not page:
            # Crawl and index the page first
            async with CrawlerEngine() as crawler:
                crawl_result = await crawler.crawl_url(url)
                if crawl_result.error:
                    return {
                        "source_url": url,
                        "results": [],
                        "took_ms": 0,
                        "error": crawl_result.error,
                    }
                page = await self._save_page(url, crawl_result.content)
                await self._index_page(page)
        
        # Find similar pages
        raw_results = await self.vector_store.find_similar_to_page(
            page_id=page.id,
            limit=num_results,
            exclude_source_domain=exclude_source_domain,
        )
        
        # Format results
        results = []
        for r in raw_results:
            result = {
                "id": r["page_id"],
                "url": r["url"],
                "title": r["title"],
                "score": r["score"],
                "published_date": r["published_date"],
                "author": r["author"],
            }
            
            if include_content:
                result["content"] = r["content"]
            
            results.append(result)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return {
            "source_url": url,
            "results": results,
            "took_ms": elapsed_ms,
        }
    
    async def _save_page(self, url: str, content) -> WebPage:
        """Save a crawled page to the database."""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        page = WebPage(
            url=url,
            domain=domain,
            title=content.title if content else None,
            description=content.description if content else None,
            content=content.content if content else None,
            markdown=content.markdown if content else None,
            author=content.author if content else None,
            published_date=content.published_date if content else None,
            language=content.language if content else None,
            content_hash=CrawlerEngine.get_content_hash(content.content) if content and content.content else None,
        )
        
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)
        
        return page
    
    async def _index_page(self, page: WebPage) -> None:
        """Index a page by generating embeddings for its chunks."""
        if not page.content:
            return
        
        # Chunk the content
        chunks = self.embedding_service.chunk_text(page.content)
        
        if not chunks:
            return
        
        # Generate embeddings
        chunk_texts = [c["content"] for c in chunks]
        embeddings = await self.embedding_service.embed_texts(chunk_texts)
        
        # Store in vector database
        await self.vector_store.upsert_chunks(
            page_id=page.id,
            chunks=chunks,
            embeddings=embeddings,
        )
    
    async def _generate_summary(self, content: str, max_length: int) -> str:
        """Generate a summary of content using Gemini."""
        import google.generativeai as genai
        
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model)
        
        prompt = f"""Summarize the following content in {max_length} words or less. 
Be concise and capture the key points:

{content[:5000]}"""  # Limit input size
        
        response = model.generate_content(prompt)
        return response.text
