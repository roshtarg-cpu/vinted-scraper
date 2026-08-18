"""HTML parser for Vinted listings."""
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone


def _extract_next_data(html):
    """
    Extract __NEXT_DATA__ JSON from Vinted page.
    
    Returns:
        dict or None
    """
    try:
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"__NEXT_DATA__ extraction failed: {e}")
    return None


def parse_listing(html):
    """
    Parse a single Vinted listing page.
    
    Returns:
        dict with item data or None
    """
    # Try __NEXT_DATA__ first
    next_data = _extract_next_data(html)
    if next_data:
        try:
            item = next_data.get('props', {}).get('pageProps', {}).get('item', {})
            if item:
                return {
                    'id': item.get('id'),
                    'title': item.get('title'),
                    'price': item.get('price'),
                    'currency': item.get('currency'),
                    'brand': item.get('brand_title'),
                    'size': item.get('size_title'),
                    'condition': item.get('status'),
                    'url': item.get('url'),
                    'photos': [p.get('url') for p in item.get('photos', [])[:3]],
                    'description': item.get('description'),
                    'user_id': item.get('user', {}).get('id'),
                    'user_login': item.get('user', {}).get('login'),
                    'created_at': item.get('created_at_ts'),
                    'scrapedAt': datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            print(f"__NEXT_DATA__ parse failed: {e}")
    
    # Fallback to HTML parsing
    soup = BeautifulSoup(html, 'html.parser')
    
    return {
        'title': soup.select_one('h1.item-title')['data-title'] if soup.select_one('h1.item-title') else None,
        'price': soup.select_one('.item-price')['data-price'] if soup.select_one('.item-price') else None,
        'brand': soup.select_one('.item-brand')['data-brand'] if soup.select_one('.item-brand') else None,
        'size': soup.select_one('.item-size')['data-size'] if soup.select_one('.item-size') else None,
        'scrapedAt': datetime.now(timezone.utc).isoformat()
    }


def parse_catalog(html):
    """
    Extract item URLs from Vinted catalog page.
    
    Returns:
        list of item URLs
    """
    urls = []
    
    # Try __NEXT_DATA__
    next_data = _extract_next_data(html)
    if next_data:
        try:
            items = next_data.get('props', {}).get('pageProps', {}).get('items', [])
            for item in items:
                url = item.get('url')
                if url:
                    # Make URL absolute if needed
                    if url.startswith('/'):
                        url = 'https://www.vinted.com' + url
                    urls.append(url)
            
            if urls:
                return urls
        except Exception as e:
            print(f"__NEXT_DATA__ catalog parse error: {e}")
    
    # Fallback to HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try multiple selectors
    links = soup.select('a.ItemBox_overlay__1kNfX, a[href*="/items/"], a.item-box__overlay')
    
    for link in links:
        href = link.get('href', '')
        if '/items/' in href:
            # Make URL absolute
            if href.startswith('/'):
                href = 'https://www.vinted.com' + href
            elif not href.startswith('http'):
                continue
            urls.append(href)
    
    return list(set(urls))  # dedupe
