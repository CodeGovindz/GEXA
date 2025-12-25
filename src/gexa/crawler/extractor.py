"""
Content extraction using Trafilatura and BeautifulSoup.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import trafilatura
from trafilatura.settings import use_config


@dataclass
class ExtractedContent:
    """Extracted content from a web page."""
    
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None  # Plain text
    markdown: Optional[str] = None  # Markdown format
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    language: Optional[str] = None
    links: List[str] = field(default_factory=list)
    word_count: int = 0


class ContentExtractor:
    """Extract clean content from HTML pages."""
    
    def __init__(self):
        # Configure trafilatura
        self.config = use_config()
        self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    
    def extract(self, url: str, html: str) -> ExtractedContent:
        """Extract content from HTML.
        
        Args:
            url: Source URL
            html: Raw HTML content
            
        Returns:
            ExtractedContent object
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Extract basic metadata from HTML
        title = self._extract_title(soup)
        description = self._extract_description(soup)
        author = self._extract_author(soup)
        published_date = self._extract_date(soup)
        language = self._extract_language(soup)
        links = self._extract_links(soup, url)
        
        # Use trafilatura for main content extraction
        content = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
            config=self.config,
        )
        
        # Get markdown version
        markdown = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            output_format="markdown",
            no_fallback=False,
            favor_precision=True,
            config=self.config,
        )
        
        # Calculate word count
        word_count = len(content.split()) if content else 0
        
        return ExtractedContent(
            url=url,
            title=title,
            description=description,
            content=content,
            markdown=markdown,
            author=author,
            published_date=published_date,
            language=language,
            links=links,
            word_count=word_count,
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        
        # Try regular title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page description."""
        # Try og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()
        
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author name."""
        # Try meta author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"].strip()
        
        # Try article:author
        article_author = soup.find("meta", property="article:author")
        if article_author and article_author.get("content"):
            return article_author["content"].strip()
        
        # Try schema.org author
        author_elem = soup.find(attrs={"itemprop": "author"})
        if author_elem:
            name_elem = author_elem.find(attrs={"itemprop": "name"})
            if name_elem:
                return name_elem.get_text().strip()
            return author_elem.get_text().strip()
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publication date."""
        date_str = None
        
        # Try various meta tags
        for attr in [
            ("property", "article:published_time"),
            ("property", "og:published_time"),
            ("name", "date"),
            ("name", "pubdate"),
            ("itemprop", "datePublished"),
        ]:
            elem = soup.find("meta", attrs={attr[0]: attr[1]})
            if elem and elem.get("content"):
                date_str = elem["content"]
                break
        
        # Try time element
        if not date_str:
            time_elem = soup.find("time", attrs={"datetime": True})
            if time_elem:
                date_str = time_elem["datetime"]
        
        if date_str:
            return self._parse_date(date_str)
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        # Common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:30], fmt)
            except ValueError:
                continue
        
        return None
    
    def _extract_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page language."""
        # Try html lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            lang = html_tag["lang"]
            # Return just the language code (e.g., "en" from "en-US")
            return lang.split("-")[0].lower()
        
        # Try meta language
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang and meta_lang.get("content"):
            return meta_lang["content"].split("-")[0].lower()
        
        return None
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page."""
        links = []
        parsed_base = urlparse(base_url)
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            
            # Skip anchors, javascript, and mailto
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            
            # Skip very long URLs (likely data URIs)
            if len(href) > 2000:
                continue
            
            links.append(href)
        
        return links
    
    def get_highlights(
        self,
        content: str,
        query: str,
        max_highlights: int = 3,
        context_chars: int = 150,
    ) -> List[str]:
        """Get relevant highlights from content based on query.
        
        Args:
            content: Text content
            query: Search query
            max_highlights: Maximum number of highlights
            context_chars: Characters of context around match
            
        Returns:
            List of highlighted text snippets
        """
        if not content or not query:
            return []
        
        highlights = []
        query_words = query.lower().split()
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Score sentences by query word matches
        scored_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for word in query_words if word in sentence_lower)
            if score > 0:
                scored_sentences.append((score, sentence))
        
        # Sort by score and take top highlights
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        for _, sentence in scored_sentences[:max_highlights]:
            # Truncate if too long
            if len(sentence) > context_chars * 2:
                sentence = sentence[:context_chars * 2] + "..."
            highlights.append(sentence.strip())
        
        return highlights
