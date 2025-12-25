"""
Crawl API endpoint.
"""

import asyncio
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey, CrawlJob, WebPage
from gexa.database.schemas import CrawlRequest, CrawlResponse, CrawlStatusResponse
from gexa.api.auth import get_api_key, increment_quota
from gexa.crawler import CrawlerEngine
from gexa.search import SearchService


router = APIRouter()


async def run_crawl_job(job_id: str, seed_url: str, max_pages: int, include_subdomains: bool):
    """Background task to run a crawl job."""
    from gexa.database.connection import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        # Get the job
        result = await db.execute(
            select(CrawlJob).where(CrawlJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return
        
        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        await db.commit()
        
        try:
            service = SearchService(db)
            
            async with CrawlerEngine() as crawler:
                async def progress_callback(crawled, total, result):
                    job.pages_crawled = crawled
                    await db.commit()
                
                results = await crawler.crawl_site(
                    seed_url=seed_url,
                    max_pages=max_pages,
                    include_subdomains=include_subdomains,
                    callback=progress_callback,
                )
                
                # Index successful crawls
                indexed_count = 0
                for crawl_result in results:
                    if crawl_result.content and not crawl_result.error:
                        try:
                            # Save and index the page
                            page = await service._save_page(
                                crawl_result.url,
                                crawl_result.content,
                            )
                            await service._index_page(page)
                            indexed_count += 1
                            
                            job.pages_indexed = indexed_count
                            await db.commit()
                        except Exception as e:
                            # Skip pages that fail to index
                            print(f"Failed to index {crawl_result.url}: {e}")
                            continue
            
            # Update job as completed
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            await db.commit()
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()


@router.post("", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Start a website crawl job.
    
    Crawls a website starting from the provided URL. The crawl runs
    in the background and pages are indexed as they are discovered.
    Use the status endpoint to check progress.
    """
    try:
        # Parse domain from URL
        parsed = urlparse(request.url)
        domain = parsed.netloc
        
        # Create crawl job
        job = CrawlJob(
            api_key_id=api_key.id,
            seed_url=request.url,
            domain=domain,
            max_pages=request.max_pages,
            status="pending",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Start background crawl
        background_tasks.add_task(
            run_crawl_job,
            str(job.id),
            request.url,
            request.max_pages,
            request.include_subdomains,
        )
        
        # Increment quota
        await increment_quota(api_key, db)
        
        return CrawlResponse(
            job_id=str(job.id),
            status="pending",
            seed_url=request.url,
            max_pages=request.max_pages,
            message="Crawl job started. Use /crawl/status/{job_id} to check progress.",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(
    job_id: str,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Get the status of a crawl job."""
    try:
        result = await db.execute(
            select(CrawlJob).where(CrawlJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Crawl job not found")
        
        # Check ownership
        if job.api_key_id != api_key.id:
            raise HTTPException(status_code=403, detail="Access denied to this crawl job")
        
        return CrawlStatusResponse(
            job_id=str(job.id),
            status=job.status,
            pages_crawled=job.pages_crawled,
            pages_indexed=job.pages_indexed,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
