"""
Embedding generation service using Google Gemini.
"""

import asyncio
from typing import List, Optional

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from gexa.config import settings


class EmbeddingService:
    """Generate embeddings using Google Gemini API."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        # Run in thread pool since genai is synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document",
            )
        )
        return result["embedding"]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query.
        
        Args:
            query: Search query
            
        Returns:
            Embedding vector as list of floats
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: genai.embed_content(
                model=self.model,
                content=query,
                task_type="retrieval_query",
            )
        )
        return result["embedding"]
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Process in batches to avoid rate limits
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Embed each text in the batch
            tasks = [self.embed_text(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            all_embeddings.extend(batch_embeddings)
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.5)
        
        return all_embeddings
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> List[dict]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of dicts with 'content', 'start_char', 'end_char'
        """
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        if not text or len(text) <= chunk_size:
            return [{"content": text, "start_char": 0, "end_char": len(text)}]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at a sentence boundary
            if end < len(text):
                # Look for sentence end within last 20% of chunk
                search_start = start + int(chunk_size * 0.8)
                search_text = text[search_start:end]
                
                for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n"]:
                    sep_pos = search_text.rfind(sep)
                    if sep_pos != -1:
                        end = search_start + sep_pos + len(sep)
                        break
            else:
                end = len(text)
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "start_char": start,
                    "end_char": end,
                })
            
            # Move start position with overlap
            start = end - chunk_overlap
            
            # Ensure we make progress
            if start <= chunks[-1]["start_char"] if chunks else 0:
                start = end
        
        return chunks
