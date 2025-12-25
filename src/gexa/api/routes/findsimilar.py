"""
Find Similar API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import FindSimilarRequest, FindSimilarResponse, SearchResult
from gexa.api.auth import get_api_key, increment_quota
from gexa.search import SearchService


router = APIRouter()


@router.post("", response_model=FindSimilarResponse)
async def find_similar(
    request: FindSimilarRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Find pages similar to a given URL.
    
    Finds web pages that are semantically similar to the content
    of the provided URL. The source page is crawled if not already
    in the index.
    """
    try:
        service = SearchService(db)
        
        result = await service.find_similar(
            url=request.url,
            num_results=request.num_results,
            include_content=request.include_content,
            exclude_source_domain=request.exclude_source_domain,
        )
        
        # Increment quota
        await increment_quota(api_key, db)
        
        # Check for errors
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
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
            )
            for r in result["results"]
        ]
        
        return FindSimilarResponse(
            source_url=result["source_url"],
            results=results,
            took_ms=result["took_ms"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
