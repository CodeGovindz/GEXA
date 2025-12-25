"""
Search API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import SearchRequest, SearchResponse, SearchResult
from gexa.api.auth import get_api_key, increment_quota
from gexa.search import SearchService


router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Perform semantic web search.
    
    Search across indexed web pages using semantic similarity.
    Returns ranked results with optional content and highlights.
    """
    try:
        service = SearchService(db)
        
        result = await service.search(
            query=request.query,
            num_results=request.num_results,
            include_content=request.include_content,
            include_highlights=request.include_highlights,
            filters=request.filters,
            api_key=api_key,
        )
        
        # Increment quota
        await increment_quota(api_key, db)
        
        # Convert to response model
        results = [
            SearchResult(
                id=r["id"],
                url=r["url"],
                title=r.get("title"),
                score=r["score"],
                published_date=r.get("published_date"),
                author=r.get("author"),
                content=r.get("content"),
                highlights=r.get("highlights"),
            )
            for r in result["results"]
        ]
        
        return SearchResponse(
            query=result["query"],
            results=results,
            total_results=result["total_results"],
            took_ms=result["took_ms"],
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
