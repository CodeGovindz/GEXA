"""
Vector store operations using pgvector.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database.models import PageChunk, WebPage
from gexa.config import settings


class VectorStore:
    """Vector search operations using PostgreSQL pgvector."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.dimension = settings.embedding_dimension
    
    async def upsert_chunks(
        self,
        page_id: UUID,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> List[PageChunk]:
        """Insert or update page chunks with embeddings.
        
        Args:
            page_id: ID of the parent web page
            chunks: List of chunk dicts with 'content', 'start_char', 'end_char'
            embeddings: Corresponding embeddings for each chunk
            
        Returns:
            List of created PageChunk objects
        """
        # Delete existing chunks for this page
        await self.db.execute(
            text("DELETE FROM page_chunks WHERE page_id = :page_id"),
            {"page_id": page_id}
        )
        
        # Insert new chunks
        page_chunks = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            page_chunk = PageChunk(
                page_id=page_id,
                chunk_index=i,
                content=chunk["content"],
                embedding=embedding,
                start_char=chunk.get("start_char"),
                end_char=chunk.get("end_char"),
            )
            self.db.add(page_chunk)
            page_chunks.append(page_chunk)
        
        await self.db.commit()
        return page_chunks
    
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            filters: Optional filters (domains, date range, etc.)
            
        Returns:
            List of search results with scores
        """
        # Build the base query with cosine similarity
        # pgvector uses <=> for cosine distance (1 - similarity)
        query = """
            SELECT 
                pc.id as chunk_id,
                pc.content as chunk_content,
                pc.chunk_index,
                wp.id as page_id,
                wp.url,
                wp.title,
                wp.domain,
                wp.author,
                wp.published_date,
                wp.content as page_content,
                1 - (pc.embedding <=> :query_embedding::vector) as score
            FROM page_chunks pc
            JOIN web_pages wp ON pc.page_id = wp.id
            WHERE pc.embedding IS NOT NULL
        """
        
        params = {"query_embedding": str(query_embedding)}
        
        # Apply filters
        if filters:
            if filters.get("domains"):
                domains = filters["domains"]
                query += " AND wp.domain = ANY(:domains)"
                params["domains"] = domains
            
            if filters.get("exclude_domains"):
                exclude = filters["exclude_domains"]
                query += " AND wp.domain != ALL(:exclude_domains)"
                params["exclude_domains"] = exclude
            
            if filters.get("start_date"):
                query += " AND wp.published_date >= :start_date"
                params["start_date"] = filters["start_date"]
            
            if filters.get("end_date"):
                query += " AND wp.published_date <= :end_date"
                params["end_date"] = filters["end_date"]
            
            if filters.get("language"):
                query += " AND wp.language = :language"
                params["language"] = filters["language"]
        
        # Order by similarity score
        query += " ORDER BY score DESC LIMIT :limit"
        params["limit"] = limit
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        # Deduplicate by page (keep highest scoring chunk per page)
        seen_pages = set()
        results = []
        
        for row in rows:
            page_id = str(row.page_id)
            if page_id in seen_pages:
                continue
            seen_pages.add(page_id)
            
            results.append({
                "chunk_id": str(row.chunk_id),
                "page_id": page_id,
                "url": row.url,
                "title": row.title,
                "domain": row.domain,
                "author": row.author,
                "published_date": row.published_date,
                "content": row.page_content,
                "chunk_content": row.chunk_content,
                "score": float(row.score),
            })
        
        return results
    
    async def find_similar_to_page(
        self,
        page_id: UUID,
        limit: int = 10,
        exclude_source_domain: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find pages similar to a given page.
        
        Args:
            page_id: ID of the source page
            limit: Maximum number of results
            exclude_source_domain: Whether to exclude same domain
            
        Returns:
            List of similar pages with scores
        """
        # Get the page's chunks and their embeddings
        result = await self.db.execute(
            select(PageChunk, WebPage)
            .join(WebPage)
            .where(PageChunk.page_id == page_id)
            .order_by(PageChunk.chunk_index)
            .limit(1)  # Use first chunk as representative
        )
        row = result.first()
        
        if not row:
            return []
        
        chunk, page = row
        
        # Build query excluding the source page
        query = """
            SELECT 
                pc.id as chunk_id,
                wp.id as page_id,
                wp.url,
                wp.title,
                wp.domain,
                wp.author,
                wp.published_date,
                wp.content,
                1 - (pc.embedding <=> :query_embedding::vector) as score
            FROM page_chunks pc
            JOIN web_pages wp ON pc.page_id = wp.id
            WHERE pc.embedding IS NOT NULL
            AND wp.id != :source_page_id
        """
        
        params = {
            "query_embedding": str(list(chunk.embedding)),
            "source_page_id": page_id,
        }
        
        if exclude_source_domain:
            query += " AND wp.domain != :source_domain"
            params["source_domain"] = page.domain
        
        query += " ORDER BY score DESC LIMIT :limit"
        params["limit"] = limit * 3  # Get extra for deduplication
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        # Deduplicate by page
        seen_pages = set()
        results = []
        
        for row in rows:
            if len(results) >= limit:
                break
            
            page_id_str = str(row.page_id)
            if page_id_str in seen_pages:
                continue
            seen_pages.add(page_id_str)
            
            results.append({
                "page_id": page_id_str,
                "url": row.url,
                "title": row.title,
                "domain": row.domain,
                "author": row.author,
                "published_date": row.published_date,
                "content": row.content,
                "score": float(row.score),
            })
        
        return results
    
    async def get_page_by_url(self, url: str) -> Optional[WebPage]:
        """Get a page by its URL."""
        result = await self.db.execute(
            select(WebPage).where(WebPage.url == url)
        )
        return result.scalar_one_or_none()
