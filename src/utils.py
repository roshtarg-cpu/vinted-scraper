"""Utility functions for Vinted scraper."""
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async


def _parse_proxy(proxy_url):
    """Parse proxy URL into dict for Playwright."""
    if not proxy_url:
        return None
    
    parsed = urlparse(proxy_url)
    proxy_dict = {
        'server': f'{parsed.scheme}://{parsed.hostname}:{parsed.port}'
    }
    
    if parsed.username and parsed.password:
        proxy_dict['username'] = parsed.username
        proxy_dict['password'] = parsed.password
    
    return proxy_dict


async def _fetch(url, proxy_url=None):
    """
    Fetch a page using Playwright with stealth mode.
    
    Args:
        url: Page URL to fetch
        proxy_url: Optional proxy URL string
        
    Returns:
        HTML content string or None if failed
    """
    proxy = _parse_proxy(proxy_url)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Apply stealth
        await stealth_async(page)
        
        try:
            response = await page.goto(url, wait_until='networkidle', timeout=90000)
            
            # Wait for content to load
            await page.wait_for_timeout(3000)
            
            html = await page.content()
            
            # Validate response
            if not response or response.status >= 400:
                print(f"Bad response status: {response.status if response else 'None'}")
                return None
            
            if len(html) < 500:
                print(f"HTML too short: {len(html)} bytes")
                return None
            
            return html
            
        except Exception as e:
            print(f"Fetch error for {url}: {e}")
            return None
        finally:
            await browser.close()
