"""
News article parser for extracting structured data from news websites.
"""

import re
from typing import Optional
from bs4 import BeautifulSoup

from gexa.parsers.base import BaseParser, ParserResult
from gexa.parsers.registry import ParserRegistry


@ParserRegistry.register
class NewsParser(BaseParser):
    """Parser for news articles and blog posts."""
    
    parser_id = "news"
    
    supported_domains = [
        "bbc.com", "bbc.co.uk",
        "cnn.com",
        "nytimes.com",
        "theguardian.com",
        "reuters.com",
        "apnews.com",
        "washingtonpost.com",
        "techcrunch.com",
        "theverge.com",
        "wired.com",
        "arstechnica.com",
        "medium.com",
        "dev.to",
        "hackernews.com",
    ]
    
    url_patterns = [
        r"/article/",
        r"/news/",
        r"/story/",
        r"/post/",
        r"/blog/",
        r"\d{4}/\d{2}/\d{2}/",  # Date-based URLs
    ]
    
    def parse(self, html: str, url: str) -> ParserResult:
        """Extract structured news article data."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            result = ParserResult()
            
            # Extract title
            result.title = self._extract_title(soup)
            
            # Extract author
            result.author = self._extract_author(soup)
            
            # Extract published date
            result.published_date = self._extract_date(soup)
            
            # Extract description
            result.description = self._extract_description(soup)
            
            # Extract main content
            result.content = self._extract_content(soup)
            
            # Extract images
            result.images = self._extract_images(soup, url)
            result.thumbnail = result.images[0] if result.images else None
            
            # Structured data
            result.data = {
                "type": "news_article",
                "title": result.title,
                "author": result.author,
                "published_date": result.published_date,
                "description": result.description,
                "word_count": len(result.content.split()) if result.content else 0,
            }
            
            return result
            
        except Exception as e:
            return ParserResult(success=False, error=str(e))
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title."""
        # Try multiple selectors
        selectors = [
            'h1.headline', 'h1.article-title', 'h1.entry-title',
            'article h1', '.post-title h1', 'h1[itemprop="headline"]',
            'meta[property="og:title"]', 'meta[name="twitter:title"]',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                return element.get_text(strip=True)
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article author."""
        selectors = [
            '.author-name', '.byline', '[rel="author"]',
            'meta[name="author"]', '[itemprop="author"]',
            '.post-author', '.article-author'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                return element.get_text(strip=True)
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date."""
        selectors = [
            'time[datetime]', 'meta[property="article:published_time"]',
            'meta[name="date"]', '.publish-date', '.post-date',
            '[itemprop="datePublished"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                if element.name == 'time':
                    return element.get('datetime', element.get_text(strip=True))
                return element.get_text(strip=True)
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article description/summary."""
        selectors = [
            'meta[property="og:description"]',
            'meta[name="description"]',
            '.article-summary', '.post-excerpt', '.lede'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                return element.get_text(strip=True)
        
        return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content."""
        # Remove unwanted elements
        for element in soup.select('nav, footer, header, aside, script, style, .ads, .sidebar'):
            element.decompose()
        
        # Try article body selectors
        selectors = [
            'article', '.article-body', '.post-content', '.entry-content',
            '.story-body', 'main', '[itemprop="articleBody"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator=' ', strip=True)
        
        # Fallback to body
        return soup.body.get_text(separator=' ', strip=True) if soup.body else ""
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract article images."""
        from urllib.parse import urljoin
        
        images = []
        
        # Try og:image first
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.get('content'):
            images.append(og_image['content'])
        
        # Get article images
        for img in soup.select('article img, .post-content img, .entry-content img'):
            src = img.get('src') or img.get('data-src')
            if src:
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, src)
                if full_url not in images:
                    images.append(full_url)
        
        return images[:5]  # Limit to 5 images
