"""
Web scraping service
Based on scrapTheWeb.py with modifications for LangGraph integration
"""
import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, List
import random

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


def clean_list(items: List[str]) -> str:
    """Clean and deduplicate list items"""
    seen = set()
    clean_items = []
    for item in items:
        item = item.strip()
        if item and item not in seen:
            clean_items.append(item)
            seen.add(item)
    return " ".join(clean_items)


def scrape_web_page(url: str) -> Dict:
    """Scrape a web page and extract structured content"""
    soup = None
    html_content = None
    
    try:
        user_agents = get_user_agents()
        headers = random.choice(user_agents)
        
        html_content = requests.get(url, headers=headers, timeout=30)
        if html_content.status_code == 200:
            soup = BeautifulSoup(html_content.text, 'html.parser')
            logger.info(f"Successfully fetched URL: {url}")
        else:
            html_content.raise_for_status()
            
    except Exception as e:
        logger.error(f"Error fetching URL: {url} - {e}")
        raise Exception(f"Failed to fetch URL: {str(e)}")
    
    if soup is None:
        raise Exception("Failed to parse HTML content")
    
    # Extract various content elements
    try:
        lang = soup.html.get('lang') if soup.html else None
    except Exception as e:
        logger.warning(f"Error extracting language: {e}")
        lang = None
    
    try:
        title = soup.title.string if soup.title else None
    except Exception as e:
        logger.warning(f"Error extracting title: {e}")
        title = None
    
    try:
        meta = [f"{meta.get('name')}: {meta.get('content')}" 
                for meta in soup.find_all('meta') if meta.get('name')]
    except Exception as e:
        logger.warning(f"Error extracting meta tags: {e}")
        meta = []
    
    try:
        headings = [heading.get_text() for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
    except Exception as e:
        logger.warning(f"Error extracting headings: {e}")
        headings = []
    
    try:
        # Extract main content (paragraphs)
        texts = [text.get_text().strip() for text in soup.find_all('p')]
        filtered_texts = [text for text in texts if text]
    except Exception as e:
        logger.warning(f"Error extracting texts: {e}")
        filtered_texts = []
    
    try:
        list_tags = soup.find_all(['ul', 'ol'])
        list_items = []
        for list_tag in list_tags:
            items = [li.get_text() for li in list_tag.find_all('li')]
            list_items.extend(items)
    except Exception as e:
        logger.warning(f"Error extracting list items: {e}")
        list_items = []
    
    # Combine all text content
    all_text = " ".join([
        title or "",
        " ".join(headings),
        " ".join(filtered_texts),
        " ".join(list_items)
    ])
    
    # Clean and format
    all_text = re.sub(r'\s+', ' ', all_text).strip()
    
    page_analysis = {
        'url': url,
        'title': title,
        'language': lang,
        'text': all_text,
        'headings': clean_list(headings),
        'meta_tags': clean_list(meta),
    }
    
    return page_analysis


async def scrape_and_store(url: str, vector_store) -> Dict:
    """Scrape a web page and store it in the vector database"""
    try:
        # Scrape the page
        page_data = scrape_web_page(url)
        
        # Split text into chunks
        from app.services.document_processor import DocumentProcessor
        chunks = DocumentProcessor.split_text(page_data['text'], chunk_size=1000, chunk_overlap=200)
        
        # Prepare metadata
        metadatas = []
        for i in range(len(chunks)):
            metadatas.append({
                'source_type': 'web_page',
                'source': url,
                'title': page_data.get('title', ''),
                'chunk_index': i
            })
        
        # Store in vector database
        ids = await vector_store.add_documents(
            texts=chunks,
            metadatas=metadatas
        )
        
        return {
            'status': 'success',
            'url': url,
            'title': page_data.get('title', ''),
            'chunks_stored': len(chunks),
            'ids': ids
        }
        
    except Exception as e:
        logger.error(f"Error scraping and storing URL {url}: {e}")
        raise

