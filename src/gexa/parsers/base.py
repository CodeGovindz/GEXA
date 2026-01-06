"""
Base parser interface for content extraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class ParserResult:
    """Result from a parser."""
    
    # Core fields
    title: Optional[str] = None
    content: Optional[str] = None
    
    # Metadata
    author: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    
    # Structured data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Images
    images: List[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    
    # Status
    success: bool = True
    error: Optional[str] = None


class BaseParser(ABC):
    """Base class for content parsers."""
    
    # Parser identifier
    parser_id: str = "base"
    
    # Domains this parser handles
    supported_domains: List[str] = []
    
    # URL patterns this parser handles (regex)
    url_patterns: List[str] = []
    
    @abstractmethod
    def parse(self, html: str, url: str) -> ParserResult:
        """
        Parse HTML content and extract structured data.
        
        Args:
            html: Raw HTML content
            url: Source URL
            
        Returns:
            ParserResult with extracted data
        """
        pass
    
    def can_parse(self, url: str) -> bool:
        """Check if this parser can handle the given URL."""
        import re
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check domain match
        for supported_domain in self.supported_domains:
            if supported_domain in domain:
                return True
        
        # Check URL pattern match
        for pattern in self.url_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
