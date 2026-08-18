"""Main Vinted scraper actor using PlaywrightCrawler."""
from apify import Actor, Request
from apify.storages import Dataset
from crawlee.playwright import PlaywrightCrawler, PlaywrightCrawlingContext
from .parser import parse_catalog, parse_listing


async def main():
    """Main actor entrypoint."""
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        search_url = actor_input.get('searchUrl', 'https://www.vinted.com/catalog')
        max_results = actor_input.get('maxResults', 50)
        proxy_config = actor_input.get('proxyConfiguration', {})
        
        scraped_count = 0
        dataset = await Dataset.open()
        
        # Router for different page types
        async def catalog_handler(context: PlaywrightCrawlingContext):
            """Handle catalog pages."""
            Actor.log.info(f'Crawling catalog: {context.request.url}')
            
            html = await context.page.content()
            item_urls = parse_catalog(html)
            
            Actor.log.info(f'Found {len(item_urls)} items')
            
            # Enqueue item URLs
            for url in item_urls[:max_results]:
                if scraped_count >= max_results:
                    break
                await context.add_requests([Request.from_url(url, label='item')])
        
        async def item_handler(context: PlaywrightCrawlingContext):
            """Handle item pages."""
            nonlocal scraped_count
            
            if scraped_count >= max_results:
                return
            
            Actor.log.info(f'Scraping item: {context.request.url}')
            
            html = await context.page.content()
            item = parse_listing(html)
            
            if item and item.get('title'):
                await dataset.push_data(item)
                scraped_count += 1
                
                if scraped_count % 10 == 0:
                    Actor.log.info(f'Progress: {scraped_count}/{max_results} items')
            else:
                Actor.log.warning(f'Failed to parse item {context.request.url}')
        
        # Create crawler
        crawler = PlaywrightCrawler(
            headless=True,
            browser_type='chromium',
            proxy_configuration=await Actor.create_proxy_configuration(proxy_config) if proxy_config.get('useApifyProxy') else None,
            request_handler_timeout_secs=120,
            max_request_retries=3,
        )
        
        # Add router
        crawler.router.default_handler = catalog_handler
        crawler.router.add_handler('item', item_handler)
        
        # Start crawling
        Actor.log.info(f'Starting Vinted scraper: {search_url}')
        await crawler.run([search_url])
        
        Actor.log.info(f'Scraping complete! Total items: {scraped_count}')
