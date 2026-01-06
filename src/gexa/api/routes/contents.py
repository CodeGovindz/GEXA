"""
Contents API endpoint with multiple output formats.
Supports: HTML, Markdown, Text, and Screenshot output.
"""

import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import ContentsRequest, ContentsResponse, PageContent
from gexa.api.auth import get_api_key, increment_quota
from gexa.crawler import CrawlerEngine
from gexa.utils.formatters import ContentFormatter


router = APIRouter()


@router.post("", response_model=ContentsResponse)
async def get_contents(
    request: ContentsRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Get clean content from URLs in multiple formats.
    
    Fetch and extract content from web pages. Returns content in
    requested formats: html, markdown, text, and/or screenshot.
    
    Features:
    - Multiple output formats (like Olostep)
    - Boilerplate removal using readability algorithm
    - Screenshot capture using Playwright
    - AI-generated summaries (optional)
    """
    start_time = time.time()
    
    try:
        results = []
        
        for url in request.urls:
            try:
                # Crawl the URL to get raw HTML
                async with CrawlerEngine() as crawler:
                    crawl_result = await crawler.crawl_url(url)
                
                if crawl_result.error:
                    results.append(PageContent(
                        url=url,
                        status="error",
                        error=crawl_result.error
                    ))
                    continue
                
                # Get the raw HTML (stored by crawler for use with formatters)
                raw_html = crawl_result.raw_html if crawl_result.raw_html else ""
                
                # Check if screenshot is requested
                needs_screenshot = 'screenshot' in request.formats
                
                if needs_screenshot:
                    # Use async formatter with screenshot
                    formatted = await ContentFormatter.format_with_screenshot(
                        html=raw_html,
                        url=url,
                        formats=request.formats,
                        remove_boilerplate=request.remove_boilerplate,
                        full_page=request.screenshot_full_page
                    )
                else:
                    # Use sync formatter (faster)
                    formatted = ContentFormatter.format_content(
                        html=raw_html,
                        url=url,
                        formats=request.formats,
                        remove_boilerplate=request.remove_boilerplate
                    )
                
                # Build response
                page_content = PageContent(
                    url=url,
                    title=formatted.get('title') or (crawl_result.content.title if crawl_result.content else None),
                    content=formatted.get('text'),
                    html=formatted.get('html'),
                    markdown=formatted.get('markdown'),
                    screenshot=formatted.get('screenshot'),
                    author=crawl_result.content.author if crawl_result.content else None,
                    published_date=crawl_result.content.published_date if crawl_result.content else None,
                    status="success"
                )
                
                # TODO: Add AI summary if requested
                # if request.include_summary:
                #     page_content.summary = await generate_summary(page_content.content)
                
                results.append(page_content)
                
            except Exception as e:
                results.append(PageContent(
                    url=url,
                    status="error",
                    error=str(e)
                ))
        
        # Increment quota based on number of URLs
        await increment_quota(api_key, db, amount=len(request.urls))
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return ContentsResponse(
            results=results,
            took_ms=elapsed_ms,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
