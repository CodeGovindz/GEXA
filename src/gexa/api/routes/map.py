"""
Map API endpoint for URL discovery.
Discovers all URLs on a domain via sitemap.xml, robots.txt, and shallow crawling.
Similar to Olostep's /maps endpoint.
"""

import asyncio
import time
import re
import xml.etree.ElementTree as ET
from typing import List, Set, Dict
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import MapRequest, MapResponse
from gexa.api.auth import get_api_key, increment_quota


router = APIRouter()


async def fetch_url(client: httpx.AsyncClient, url: str) -> str:
    """Fetch URL content with error handling."""
    try:
        response = await client.get(url, timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return ""


async def parse_sitemap(client: httpx.AsyncClient, base_url: str) -> Set[str]:
    """Parse sitemap.xml and extract URLs."""
    urls = set()
    
    # Common sitemap locations
    sitemap_urls = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
        urljoin(base_url, "/sitemap/sitemap.xml"),
    ]
    
    for sitemap_url in sitemap_urls:
        content = await fetch_url(client, sitemap_url)
        if not content:
            continue
            
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Handle sitemap index (contains references to other sitemaps)
            for sitemap in root.iter():
                if sitemap.tag.endswith('loc'):
                    loc = sitemap.text.strip() if sitemap.text else ""
                    if loc:
                        # Check if it's a nested sitemap
                        if loc.endswith('.xml'):
                            nested_content = await fetch_url(client, loc)
                            if nested_content:
                                try:
                                    nested_root = ET.fromstring(nested_content)
                                    for nested_loc in nested_root.iter():
                                        if nested_loc.tag.endswith('loc'):
                                            if nested_loc.text:
                                                urls.add(nested_loc.text.strip())
                                except ET.ParseError:
                                    pass
                        else:
                            urls.add(loc)
        except ET.ParseError:
            continue
    
    return urls


async def parse_robots(client: httpx.AsyncClient, base_url: str) -> Set[str]:
    """Parse robots.txt and extract Allow/Sitemap paths."""
    urls = set()
    
    robots_url = urljoin(base_url, "/robots.txt")
    content = await fetch_url(client, robots_url)
    
    if not content:
        return urls
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Extract Sitemap URLs
        if line.lower().startswith('sitemap:'):
            sitemap_url = line.split(':', 1)[1].strip()
            if sitemap_url:
                # Parse the sitemap
                sitemap_urls = await parse_sitemap(client, sitemap_url)
                urls.update(sitemap_urls)
        
        # Extract Allow paths
        elif line.lower().startswith('allow:'):
            path = line.split(':', 1)[1].strip()
            if path and not path.startswith('*'):
                # Convert path to full URL
                full_url = urljoin(base_url, path)
                urls.add(full_url)
    
    return urls


async def shallow_crawl(client: httpx.AsyncClient, base_url: str, max_urls: int = 50) -> Set[str]:
    """Perform shallow crawl to discover URLs from homepage links."""
    urls = set()
    
    # Fetch homepage
    content = await fetch_url(client, base_url)
    if not content:
        return urls
    
    # Extract href links using regex (faster than full HTML parsing)
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    
    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
    matches = href_pattern.findall(content)
    
    for href in matches:
        if len(urls) >= max_urls:
            break
            
        # Skip anchors, javascript, mailto, etc.
        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        
        # Convert to absolute URL
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        
        # Only include URLs from same domain
        if parsed_url.netloc == base_domain or not parsed_url.netloc:
            # Normalize URL (remove fragment)
            clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            if parsed_url.query:
                clean_url += f"?{parsed_url.query}"
            urls.add(clean_url)
    
    return urls


@router.post("", response_model=MapResponse)
async def map_domain(
    request: MapRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Discover all URLs on a domain.
    
    Uses multiple sources to find URLs:
    - sitemap.xml parsing
    - robots.txt parsing  
    - Shallow link crawling
    
    Similar to Olostep's /maps endpoint.
    """
    start_time = time.time()
    
    try:
        # Normalize base URL
        parsed = urlparse(request.url)
        if not parsed.scheme:
            base_url = f"https://{request.url}"
        else:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        all_urls: Set[str] = set()
        sources: Dict[str, int] = {}
        
        async with httpx.AsyncClient(
            headers={"User-Agent": "GEXA-Bot/1.0"},
            follow_redirects=True
        ) as client:
            
            # 1. Parse sitemap.xml
            if request.use_sitemap:
                sitemap_urls = await parse_sitemap(client, base_url)
                sources["sitemap"] = len(sitemap_urls)
                all_urls.update(sitemap_urls)
            
            # 2. Parse robots.txt
            if request.use_robots:
                robots_urls = await parse_robots(client, base_url)
                new_from_robots = len(robots_urls - all_urls)
                sources["robots"] = new_from_robots
                all_urls.update(robots_urls)
            
            # 3. Shallow crawl
            if request.shallow_crawl:
                crawl_urls = await shallow_crawl(
                    client, base_url, 
                    max_urls=request.max_urls - len(all_urls)
                )
                new_from_crawl = len(crawl_urls - all_urls)
                sources["crawl"] = new_from_crawl
                all_urls.update(crawl_urls)
        
        # Filter by subdomain if needed
        base_domain = urlparse(base_url).netloc
        if not request.include_subdomains:
            all_urls = {
                url for url in all_urls 
                if urlparse(url).netloc == base_domain
            }
        
        # Limit to max_urls
        url_list = sorted(list(all_urls))[:request.max_urls]
        
        # Increment quota
        await increment_quota(api_key, db, amount=1)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return MapResponse(
            url=base_url,
            urls=url_list,
            total_urls=len(url_list),
            sources=sources,
            took_ms=elapsed_ms,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
