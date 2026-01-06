"""
E-commerce product page parser.
"""

import re
from typing import Optional, List
from bs4 import BeautifulSoup

from gexa.parsers.base import BaseParser, ParserResult
from gexa.parsers.registry import ParserRegistry


@ParserRegistry.register
class EcommerceParser(BaseParser):
    """Parser for e-commerce product pages."""
    
    parser_id = "ecommerce"
    
    supported_domains = [
        "amazon.com", "amazon.co.uk", "amazon.in",
        "ebay.com",
        "walmart.com",
        "target.com",
        "bestbuy.com",
        "etsy.com",
        "shopify.com",
        "aliexpress.com",
    ]
    
    url_patterns = [
        r"/product/",
        r"/dp/",  # Amazon
        r"/itm/",  # eBay
        r"/ip/",  # Walmart
        r"/p/",
        r"/products/",
    ]
    
    def parse(self, html: str, url: str) -> ParserResult:
        """Extract structured product data."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            result = ParserResult()
            
            # Extract product info
            result.title = self._extract_title(soup)
            result.description = self._extract_description(soup)
            
            # Extract price
            price = self._extract_price(soup)
            
            # Extract rating
            rating = self._extract_rating(soup)
            
            # Extract images
            result.images = self._extract_images(soup, url)
            result.thumbnail = result.images[0] if result.images else None
            
            # Extract availability
            availability = self._extract_availability(soup)
            
            # Structured data
            result.data = {
                "type": "product",
                "name": result.title,
                "description": result.description,
                "price": price,
                "currency": self._detect_currency(soup, price),
                "rating": rating.get("value") if rating else None,
                "review_count": rating.get("count") if rating else None,
                "availability": availability,
                "images": result.images,
            }
            
            result.content = f"{result.title}\n\nPrice: {price}\nRating: {rating}\n\n{result.description}"
            
            return result
            
        except Exception as e:
            return ParserResult(success=False, error=str(e))
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title."""
        selectors = [
            '#productTitle',  # Amazon
            'h1.x-item-title__mainTitle',  # eBay
            'h1[itemprop="name"]',
            '.product-title h1', 'h1.product-name',
            'meta[property="og:title"]',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                return element.get_text(strip=True)
        
        return None
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product price."""
        selectors = [
            '.a-price .a-offscreen',  # Amazon
            '#priceblock_ourprice', '#priceblock_dealprice',
            '.x-price-primary',  # eBay
            '[itemprop="price"]',
            '.price', '.product-price', '.current-price',
            'meta[property="product:price:amount"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                text = element.get_text(strip=True)
                # Extract numeric price
                price_match = re.search(r'[\$£€₹]?\s*[\d,]+\.?\d*', text)
                if price_match:
                    return price_match.group(0)
        
        return None
    
    def _extract_rating(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract product rating."""
        rating_data = {}
        
        # Rating value
        rating_selectors = [
            '.a-icon-star',  # Amazon
            '[itemprop="ratingValue"]',
            '.rating', '.star-rating'
        ]
        
        for selector in rating_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True) or element.get('content', '')
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    rating_data["value"] = float(match.group(1))
                    break
        
        # Review count
        count_selectors = [
            '#acrCustomerReviewText',  # Amazon
            '[itemprop="reviewCount"]',
            '.review-count', '.ratings-count'
        ]
        
        for selector in count_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True) or element.get('content', '')
                match = re.search(r'([\d,]+)', text)
                if match:
                    rating_data["count"] = int(match.group(1).replace(',', ''))
                    break
        
        return rating_data if rating_data else None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product description."""
        selectors = [
            '#productDescription',  # Amazon
            '#feature-bullets',
            '.product-description',
            '[itemprop="description"]',
            'meta[property="og:description"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                return element.get_text(separator=' ', strip=True)
        
        return None
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract product images."""
        from urllib.parse import urljoin
        
        images = []
        
        # Try og:image first
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.get('content'):
            images.append(og_image['content'])
        
        # Product gallery images
        selectors = [
            '#altImages img',  # Amazon
            '.product-gallery img',
            '.product-images img',
            '[itemprop="image"]'
        ]
        
        for selector in selectors:
            for img in soup.select(selector):
                src = img.get('src') or img.get('data-src')
                if src and 'icon' not in src.lower():
                    full_url = urljoin(base_url, src)
                    if full_url not in images:
                        images.append(full_url)
        
        return images[:5]
    
    def _extract_availability(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product availability."""
        selectors = [
            '#availability',  # Amazon
            '.availability',
            '[itemprop="availability"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True).lower()
                if 'in stock' in text:
                    return 'in_stock'
                elif 'out of stock' in text:
                    return 'out_of_stock'
                elif 'pre-order' in text:
                    return 'pre_order'
                return text
        
        return None
    
    def _detect_currency(self, soup: BeautifulSoup, price: Optional[str]) -> Optional[str]:
        """Detect currency from price or meta."""
        if price:
            if '$' in price:
                return 'USD'
            elif '£' in price:
                return 'GBP'
            elif '€' in price:
                return 'EUR'
            elif '₹' in price:
                return 'INR'
        
        # Check meta
        currency = soup.select_one('meta[property="product:price:currency"]')
        if currency:
            return currency.get('content')
        
        return None
