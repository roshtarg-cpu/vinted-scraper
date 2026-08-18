"""Utility functions for Vinted scraper."""
from urllib.parse import urlparse, parse_qs
from camoufox.async_api import AsyncCamoufox


def _parse_proxy(proxy_url):
    """Parse proxy URL into dict for Camoufox."""
    if not proxy_url:
        return None
    
    parsed = urlparse(proxy_url)
    return {
        'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
        'username': parsed.username,
        'password': parsed.password
    }


async def _fetch(url, proxy_url=None):
    """
    Fetch a page using AsyncCamoufox with Cloudflare bypass.
    
    Args:
        url: Page URL to fetch
        proxy_url: Optional proxy URL string
        
    Returns:
        HTML content string or None if failed
    """
    proxy = _parse_proxy(proxy_url)
    
    async with AsyncCamoufox(
        headless=True,
        geoip=True,
        proxy=proxy
    ) as browser:
        page = await browser.new_page()
        
        try:
            response = await page.goto(url, wait_until='networkidle', timeout=90000)
            
            # Wait for dynamic content
            await page.wait_for_timeout(3000)
            
            html = await page.content()
            
            # Validate response
            if not response or response.status >= 400:
                return None
            
            if len(html) < 500:
                return None
            
            return html
            
        except Exception as e:
            print(f"Fetch error for {url}: {e}")
            return None
        finally:
            await page.close()
