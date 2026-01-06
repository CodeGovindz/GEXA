"""
Content formatting utilities for converting HTML to various output formats.
"""

import asyncio
import base64
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from markdownify import markdownify as md
from readability import Document


def html_to_markdown(html: str, strip_tags: Optional[list] = None) -> str:
    """
    Convert HTML content to clean Markdown.
    
    Args:
        html: Raw HTML content
        strip_tags: Optional list of tags to strip (default: script, style, nav, footer)
        
    Returns:
        Clean markdown string
    """
    if not html:
        return ""
    
    # Default tags to strip for cleaner output
    if strip_tags is None:
        strip_tags = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']
    
    try:
        # Convert HTML to Markdown
        markdown = md(
            html,
            heading_style="ATX",  # Use # style headings
            bullets="-",  # Use - for bullet points
            strip=strip_tags,
            code_language="",  # Don't add language to code blocks
        )
        
        # Clean up excessive whitespace
        lines = markdown.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line = line.rstrip()
            is_empty = not line.strip()
            
            # Skip consecutive empty lines
            if is_empty and prev_empty:
                continue
                
            cleaned_lines.append(line)
            prev_empty = is_empty
        
        return '\n'.join(cleaned_lines).strip()
        
    except Exception as e:
        # If conversion fails, return raw text
        return html


def extract_article(html: str, url: str = "") -> Dict[str, Any]:
    """
    Extract main article content from HTML using readability algorithm.
    Similar to Postlight Mercury Parser.
    
    Args:
        html: Raw HTML content
        url: Optional URL for better parsing
        
    Returns:
        Dictionary with title, content, short_title, and summary
    """
    if not html:
        return {"title": "", "content": "", "short_title": "", "summary": ""}
    
    try:
        doc = Document(html, url=url if url else None)
        
        # Get cleaned HTML content
        cleaned_html = doc.summary()
        
        return {
            "title": doc.title(),
            "short_title": doc.short_title(),
            "content": cleaned_html,
            "author": None,  # readability doesn't extract author
        }
        
    except Exception as e:
        return {
            "title": "",
            "content": html,
            "short_title": "",
            "summary": "",
            "error": str(e)
        }


def extract_clean_text(html: str) -> str:
    """
    Extract plain text from HTML, removing all tags.
    
    Args:
        html: Raw HTML content
        
    Returns:
        Plain text string
    """
    if not html:
        return ""
    
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Get text with proper spacing
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up multiple spaces
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    except Exception as e:
        return html


async def take_screenshot(url: str, full_page: bool = True, width: int = 1280, height: int = 720) -> Optional[bytes]:
    """
    Take a screenshot of a webpage using Playwright.
    
    Args:
        url: URL to screenshot
        full_page: Whether to capture full page or viewport only
        width: Viewport width
        height: Viewport height
        
    Returns:
        Screenshot as PNG bytes, or None if failed
    """
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            page = await browser.new_page(viewport={'width': width, 'height': height})
            
            # Navigate to URL with timeout
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for any lazy-loaded content
            await asyncio.sleep(1)
            
            # Take screenshot
            screenshot = await page.screenshot(
                full_page=full_page,
                type='png'
            )
            
            await browser.close()
            
            return screenshot
            
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None


def screenshot_to_base64(screenshot_bytes: bytes) -> str:
    """
    Convert screenshot bytes to base64 data URL.
    
    Args:
        screenshot_bytes: PNG screenshot bytes
        
    Returns:
        Base64 data URL string
    """
    if not screenshot_bytes:
        return ""
    
    b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"


class ContentFormatter:
    """
    High-level content formatting class that combines all formatters.
    """
    
    @staticmethod
    def format_content(
        html: str,
        url: str = "",
        formats: list = None,
        remove_boilerplate: bool = True
    ) -> Dict[str, Any]:
        """
        Format HTML content into multiple output formats.
        
        Args:
            html: Raw HTML content
            url: Source URL
            formats: List of formats to generate: ['html', 'markdown', 'text']
            remove_boilerplate: Whether to remove nav, footer, etc.
            
        Returns:
            Dictionary with requested format outputs
        """
        if formats is None:
            formats = ['markdown', 'text']
        
        result = {}
        
        # Extract article if removing boilerplate
        if remove_boilerplate:
            article = extract_article(html, url)
            clean_html = article.get('content', html)
            result['title'] = article.get('title', '')
        else:
            clean_html = html
            result['title'] = ''
        
        # Generate requested formats
        if 'html' in formats:
            result['html'] = clean_html
            
        if 'markdown' in formats:
            result['markdown'] = html_to_markdown(clean_html)
            
        if 'text' in formats:
            result['text'] = extract_clean_text(clean_html)
        
        return result
    
    @staticmethod
    async def format_with_screenshot(
        html: str,
        url: str,
        formats: list = None,
        remove_boilerplate: bool = True,
        full_page: bool = True
    ) -> Dict[str, Any]:
        """
        Format content including screenshot if requested.
        
        Args:
            html: Raw HTML content
            url: Source URL (required for screenshot)
            formats: List of formats including 'screenshot'
            remove_boilerplate: Whether to remove nav, footer
            full_page: Whether to capture full page
            
        Returns:
            Dictionary with all requested formats
        """
        if formats is None:
            formats = ['markdown']
        
        # Get non-screenshot formats first
        non_screenshot_formats = [f for f in formats if f != 'screenshot']
        result = ContentFormatter.format_content(
            html, url, non_screenshot_formats, remove_boilerplate
        )
        
        # Add screenshot if requested
        if 'screenshot' in formats and url:
            screenshot = await take_screenshot(url, full_page=full_page)
            if screenshot:
                result['screenshot'] = screenshot_to_base64(screenshot)
            else:
                result['screenshot'] = None
                result['screenshot_error'] = 'Failed to capture screenshot'
        
        return result
