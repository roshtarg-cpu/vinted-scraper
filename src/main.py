"""Main Vinted scraper actor."""
import os
import asyncio
from apify import Actor
from .utils import _fetch
from .parser import parse_catalog, parse_listing


async def main():
    """Main actor entrypoint."""
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        search_url = actor_input.get('searchUrl', 'https://www.vinted.com/catalog')
        max_results = actor_input.get('maxResults', 50)
        proxy_config = actor_input.get('proxyConfiguration', {})
        
        # Build proxy URL
        proxy_url = None
        if proxy_config and proxy_config.get('useApifyProxy'):
            proxy_password = os.getenv('APIFY_PROXY_PASSWORD')
            groups = proxy_config.get('apifyProxyGroups', ['RESIDENTIAL'])
            group = groups[0] if groups else 'RESIDENTIAL'
            country = proxy_config.get('apifyProxyCountry', 'US')
            # Correct Apify proxy format
            proxy_url = f'http://groups-{group},{country}:{proxy_password}@proxy.apify.com:8000'
        
        Actor.log.info(f'Starting Vinted scraper: {search_url}')
        Actor.log.info(f'Target: {max_results} items')
        Actor.log.info(f'Proxy: {proxy_url[:50] if proxy_url else "None"}...')
        
        scraped_count = 0
        page_num = 1
        
        while scraped_count < max_results:
            # Build catalog URL with pagination
            catalog_url = f'{search_url}?page={page_num}'
            
            Actor.log.info(f'Fetching catalog page {page_num}: {catalog_url}')
            
            # Fetch catalog page with retries
            html = None
            for attempt in range(3):
                html = await _fetch(catalog_url, proxy_url)
                if html:
                    break
                Actor.log.warning(f'Catalog fetch attempt {attempt + 1} failed, retrying...')
                await asyncio.sleep(2 ** attempt)
            
            if not html:
                Actor.log.error(f'Failed to fetch catalog page {page_num} after 3 attempts')
                break
            
            # Parse item URLs
            item_urls = parse_catalog(html)
            
            if not item_urls:
                Actor.log.info(f'No items found on page {page_num}, stopping')
                break
            
            Actor.log.info(f'Found {len(item_urls)} items on page {page_num}')
            
            # Scrape each item
            for item_url in item_urls:
                if scraped_count >= max_results:
                    break
                
                # Fetch item page with retries
                item_html = None
                for attempt in range(3):
                    item_html = await _fetch(item_url, proxy_url)
                    if item_html:
                        break
                    await asyncio.sleep(2 ** attempt)
                
                if not item_html:
                    Actor.log.warning(f'Failed to fetch item {item_url}')
                    continue
                
                # Parse item
                item = parse_listing(item_html)
                
                if item and item.get('title'):
                    # Push to dataset immediately
                    await Actor.push_data(item)
                    scraped_count += 1
                    
                    # Log progress every 10 items
                    if scraped_count % 10 == 0:
                        Actor.log.info(f'Progress: {scraped_count}/{max_results} items scraped')
                else:
                    Actor.log.warning(f'Failed to parse item {item_url}')
            
            page_num += 1
        
        Actor.log.info(f'Scraping complete! Total items: {scraped_count}')
