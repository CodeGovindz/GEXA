"""
Parser registry for auto-detecting and applying parsers to URLs.
"""

from typing import Optional, List, Type, Dict
from urllib.parse import urlparse

from gexa.parsers.base import BaseParser, ParserResult


class ParserRegistry:
    """Registry of content parsers with auto-detection."""
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    _instances: Dict[str, BaseParser] = {}
    
    @classmethod
    def register(cls, parser_class: Type[BaseParser]) -> Type[BaseParser]:
        """Register a parser class."""
        parser_id = parser_class.parser_id
        cls._parsers[parser_id] = parser_class
        return parser_class
    
    @classmethod
    def get_parser(cls, parser_id: str) -> Optional[BaseParser]:
        """Get a parser instance by ID."""
        if parser_id not in cls._instances:
            if parser_id in cls._parsers:
                cls._instances[parser_id] = cls._parsers[parser_id]()
        return cls._instances.get(parser_id)
    
    @classmethod
    def detect_parser(cls, url: str) -> Optional[BaseParser]:
        """Auto-detect the best parser for a URL."""
        for parser_id, parser_class in cls._parsers.items():
            if parser_id not in cls._instances:
                cls._instances[parser_id] = parser_class()
            
            parser = cls._instances[parser_id]
            if parser.can_parse(url):
                return parser
        
        return None
    
    @classmethod
    def list_parsers(cls) -> List[Dict[str, any]]:
        """List all registered parsers."""
        return [
            {
                "id": parser_id,
                "domains": parser_class.supported_domains,
                "patterns": parser_class.url_patterns,
            }
            for parser_id, parser_class in cls._parsers.items()
        ]


def get_parser(url: str, parser_id: Optional[str] = None) -> Optional[BaseParser]:
    """
    Get the appropriate parser for a URL.
    
    Args:
        url: URL to parse
        parser_id: Optional specific parser ID to use
        
    Returns:
        Parser instance or None if no suitable parser found
    """
    if parser_id:
        return ParserRegistry.get_parser(parser_id)
    return ParserRegistry.detect_parser(url)


# Import and register parsers
def _register_all_parsers():
    """Import and register all built-in parsers."""
    try:
        from gexa.parsers import news
        from gexa.parsers import ecommerce
    except ImportError:
        pass


# Register parsers on module import
_register_all_parsers()
