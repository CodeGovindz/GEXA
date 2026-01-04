"""
Answer API endpoint using Gemini for AI-generated answers.
"""

import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

from gexa.config import settings
from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import AnswerRequest, AnswerResponse, Citation
from gexa.api.auth import get_api_key, increment_quota
from gexa.search import SearchService


router = APIRouter()


@router.post("", response_model=AnswerResponse)
async def answer_question(
    request: AnswerRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Get an AI-generated answer with citations.
    
    Searches the web for relevant information and generates
    a comprehensive answer using Gemini, with citations to
    the source pages.
    """
    start_time = time.time()
    
    try:
        # Configure Gemini for query rewriting
        genai.configure(api_key=settings.gemini_api_key)
        
        # Step 1: Rewrite the user's question into an optimized search query
        # This prevents ambiguity (e.g., "capital" as city vs. money)
        rewrite_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        rewrite_prompt = f"""Convert this question into an optimal web search query.
The search query should be concise, specific, and target the exact information needed.
Remove filler words and focus on key entities and concepts.

Question: {request.query}

Search query (output ONLY the search query, nothing else):"""
        
        try:
            rewrite_response = rewrite_model.generate_content(rewrite_prompt)
            optimized_query = rewrite_response.text.strip().strip('"').strip("'")
            # Fallback to original if rewriting fails or returns empty
            if not optimized_query or len(optimized_query) < 3:
                optimized_query = request.query
        except Exception:
            # If rewriting fails, use original query
            optimized_query = request.query
        
        # Step 2: Search with the optimized query
        service = SearchService(db)
        
        search_result = await service.search(
            query=optimized_query,
            num_results=request.num_sources,
            include_content=True,
            include_highlights=True,
        )
        
        # Prepare context from search results
        context_parts = []
        citations = []
        
        for i, result in enumerate(search_result["results"]):
            if result.get("content"):
                # Truncate content to avoid token limits
                content = result["content"][:3000]
                context_parts.append(f"[Source {i+1}]: {result.get('title', 'Unknown')}\n{content}")
                
                # Create citation
                if request.include_citations:
                    snippet = result.get("highlights", [content[:200]])[0] if result.get("highlights") else content[:200]
                    citations.append(Citation(
                        url=result["url"],
                        title=result.get("title"),
                        snippet=snippet,
                    ))
        
        # Generate answer using Gemini
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model)
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Based on the following sources, answer this question: {request.query}

Sources:
{context}

Instructions:
1. Provide a comprehensive, accurate answer based on the sources
2. If the sources don't contain enough information, say so
3. Use clear, well-structured language
4. Reference specific sources when making claims (e.g., "According to Source 1...")

Answer:"""
        
        response = model.generate_content(prompt)
        answer_text = response.text
        
        # Increment quota (search + answer generation)
        await increment_quota(api_key, db, amount=2)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return AnswerResponse(
            query=request.query,
            answer=answer_text,
            citations=citations if request.include_citations else [],
            took_ms=elapsed_ms,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
