"""
Website crawler service for RAG pipeline
Crawls a website starting from a homepage URL and stores all pages in vector database
Based on gocustomai patterns for website crawling
"""
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse
import asyncio
import aiohttp
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


def get_user_agents() -> List[Dict[str, str]]:
    """Return a list of user-agent strings and additional headers"""
    return [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Cache-Control': 'max-age=0',
        },
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4.1 Safari/605.1.15',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/89.0',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'DNT': '1',
        },
    ]


def is_valid_url(url: str, base_domain: str) -> bool:
    """
    Check if URL is valid and belongs to the same domain
    """
    try:
        parsed = urlparse(url)
        base_parsed = urlparse(base_domain)
        
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Must be same domain
        if parsed.netloc != base_parsed.netloc:
            return False
        
        # Exclude common non-content URLs
        excluded_patterns = [
            '/api/', '/admin/', '/login', '/logout', '/register',
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
            '.css', '.js', '.json', '.xml', '/feed', '/rss',
            '/search', '?', '#', 'mailto:', 'tel:', 'javascript:'
        ]
        
        path = parsed.path.lower()
        if any(pattern in path for pattern in excluded_patterns):
            return False
        
        return True
    except Exception:
        return False


def extract_links(soup: BeautifulSoup, base_url: str, base_domain: str) -> Set[str]:
    """
    Extract all valid internal links from a page
    """
    links = set()
    
    try:
        for tag in soup.find_all('a', href=True):
            href = tag.get('href', '')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Remove fragments
            absolute_url = absolute_url.split('#')[0]
            
            # Validate URL
            if is_valid_url(absolute_url, base_domain):
                links.add(absolute_url)
    except Exception as e:
        logger.warning(f"Error extracting links from {base_url}: {e}")
    
    return links


async def scrape_page(session: aiohttp.ClientSession, url: str) -> Dict:
    """
    Scrape a single page and extract content
    """
    try:
        headers = get_user_agents()[0]  # Use first user agent
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch {url}: Status {response.status}")
                return None
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = soup.title.string.strip() if soup.title else url
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract main content
            text_parts = []
            
            # Get headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text_parts.append(heading.get_text().strip())
            
            # Get paragraphs
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if text:
                    text_parts.append(text)
            
            # Get list items
            for li in soup.find_all('li'):
                text = li.get_text().strip()
                if text:
                    text_parts.append(text)
            
            # Combine all text
            full_text = '\n'.join(text_parts)
            full_text = ' '.join(full_text.split())  # Normalize whitespace
            
            if not full_text.strip():
                logger.warning(f"No text content found on {url}")
                return None
            
            return {
                'url': url,
                'title': title,
                'text': full_text,
                'soup': soup  # Keep soup for link extraction
            }
            
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None


class WebsiteCrawler:
    """
    Website crawler that starts from a homepage and crawls internal pages
    """
    
    def __init__(self, max_depth: int = 2, max_pages: int = 50):
        """
        Initialize crawler
        
        Args:
            max_depth: Maximum depth to crawl (0 = homepage only, 1 = homepage + direct links, etc.)
            max_pages: Maximum number of pages to crawl
        """
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.pages_data: List[Dict] = []
        self.base_domain = None
    
    async def crawl_website(self, homepage_url: str) -> List[Dict]:
        """
        Crawl a website starting from homepage URL
        
        Args:
            homepage_url: The homepage URL to start crawling from
            
        Returns:
            List of page data dictionaries with url, title, and text
        """
        try:
            # Parse base domain
            parsed = urlparse(homepage_url)
            self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
            
            # URLs to crawl: (url, depth)
            urls_to_crawl = [(homepage_url, 0)]
            
            async with aiohttp.ClientSession() as session:
                while urls_to_crawl and len(self.pages_data) < self.max_pages:
                    # Get next URL to crawl
                    current_url, depth = urls_to_crawl.pop(0)
                    
                    # Skip if already visited or too deep
                    if current_url in self.visited_urls or depth > self.max_depth:
                        continue
                    
                    self.visited_urls.add(current_url)
                    logger.info(f"Crawling {current_url} (depth: {depth})")
                    
                    # Scrape the page
                    page_data = await scrape_page(session, current_url)
                    
                    if page_data:
                        # Store page data (without soup)
                        page_info = {
                            'url': page_data['url'],
                            'title': page_data['title'],
                            'text': page_data['text']
                        }
                        self.pages_data.append(page_info)
                        
                        # Extract links if not at max depth
                        if depth < self.max_depth:
                            links = extract_links(
                                page_data['soup'],
                                current_url,
                                self.base_domain
                            )
                            
                            # Add new links to crawl queue
                            for link in links:
                                if link not in self.visited_urls:
                                    urls_to_crawl.append((link, depth + 1))
            
            logger.info(f"Crawled {len(self.pages_data)} pages from {homepage_url}")
            return self.pages_data
            
        except Exception as e:
            logger.error(f"Error crawling website {homepage_url}: {e}")
            raise


async def crawl_and_store_website(
    homepage_url: str,
    vector_store,
    max_depth: int = 2,
    max_pages: int = 50
) -> Dict:
    """
    Crawl a website starting from homepage and store all pages in vector database
    
    Args:
        homepage_url: The homepage URL to start crawling from
        vector_store: VectorStore instance to store documents
        max_depth: Maximum crawl depth (default: 2)
        max_pages: Maximum number of pages to crawl (default: 50)
        
    Returns:
        Dictionary with crawl results
    """
    try:
        # Initialize crawler
        crawler = WebsiteCrawler(max_depth=max_depth, max_pages=max_pages)
        
        # Crawl website
        pages_data = await crawler.crawl_website(homepage_url)
        
        if not pages_data:
            raise ValueError("No pages were successfully crawled")
        
        # Process and store each page
        all_chunks = []
        all_metadatas = []
        
        processor = DocumentProcessor()
        
        for page in pages_data:
            # Split page text into chunks
            chunks = processor.split_text(
                page['text'],
                chunk_size=1000,
                chunk_overlap=200
            )
            
            # Create metadata for each chunk
            for idx, chunk_text in enumerate(chunks):
                metadata = {
                    'source_type': 'website',
                    'source': homepage_url,
                    'page_url': page['url'],
                    'page_title': page['title'],
                    'chunk_index': idx
                }
                all_chunks.append(chunk_text)
                all_metadatas.append(metadata)
        
        # Store in vector database
        ids = await vector_store.add_documents(
            texts=all_chunks,
            metadatas=all_metadatas
        )
        
        return {
            'status': 'success',
            'homepage_url': homepage_url,
            'pages_crawled': len(pages_data),
            'chunks_stored': len(all_chunks),
            'ids': ids[:10]  # Return first 10 IDs as sample
        }
        
    except Exception as e:
        logger.error(f"Error crawling and storing website {homepage_url}: {e}")
        raise

