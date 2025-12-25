"""
Contents API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import ContentsRequest, ContentsResponse, PageContent
from gexa.api.auth import get_api_key, increment_quota
from gexa.search import SearchService


router = APIRouter()


@router.post("", response_model=ContentsResponse)
async def get_contents(
    request: ContentsRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Get clean content from URLs.
    
    Fetch and extract content from web pages. Pages are crawled
    if not already in the index. Returns clean text and optional
    markdown format.
    """
    try:
        service = SearchService(db)
        
        result = await service.get_contents(
            urls=request.urls,
            include_markdown=request.include_markdown,
            include_summary=request.include_summary,
            summary_max_length=request.summary_max_length or 200,
        )
        
        # Increment quota based on number of URLs
        await increment_quota(api_key, db, amount=len(request.urls))
        
        # Convert to response model
        results = [
            PageContent(
                url=r["url"],
                title=r.get("title"),
                content=r.get("content"),
                markdown=r.get("markdown"),
                summary=r.get("summary"),
                author=r.get("author"),
                published_date=r.get("published_date"),
                status=r.get("status", "success"),
                error=r.get("error"),
            )
            for r in result["results"]
        ]
        
        return ContentsResponse(
            results=results,
            took_ms=result["took_ms"],
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
