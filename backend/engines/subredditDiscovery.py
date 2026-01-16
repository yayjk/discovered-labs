from bs4 import BeautifulSoup
from typing import List, Dict
import time
import random
from curl_cffi import requests

# Reddit search URL template
REDDIT_SEARCH_TEMPLATE = "https://old.reddit.com/search/?q={query}&sort=relevance&t=week"

# Browser user agents for rotation
USER_AGENTS = {
    "chrome_131": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome_130": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "firefox_latest": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "safari_macos": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "edge_131": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "chrome_mobile": "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
}

# Impersonate targets for curl_cffi (supported targets)
IMPERSONATE_TARGETS = ["chrome131", "chrome120", "firefox120", "safari17_0"]

def scrape_reddit_search(query: str) -> List[str]:
    """
    Scrape Reddit search results using Beautiful Soup with curl_cffi browser impersonation.
    
    Args:
        query: The search query (e.g., 'openai')
        
    Returns:
        List of subreddit names found in the search results
    """
    # Build the URL from template
    url = REDDIT_SEARCH_TEMPLATE.format(query=query)
    
    try:
        # Select random impersonate target for browser mimicking
        impersonate_target = random.choice(IMPERSONATE_TARGETS)
        
        # Fetch the page with curl_cffi for browser impersonation
        response = requests.get(url, impersonate=impersonate_target, timeout=10)
        response.raise_for_status()
        
        
        # Parse with Beautiful Soup
        soup = BeautifulSoup(response.content, 'lxml')
        
        anchor_texts = set()
        
        # Find all divs with class search-result-listing
        search_listing_divs = soup.find_all('div', class_='search-result-listing')
        print(f"Found {len(search_listing_divs)} search-result-listing divs")
        
        # Get the second one (index 1)
        if len(search_listing_divs) > 1:
            second_listing = search_listing_divs[1]
            print("Found second search-result-listing div")
            
            # Find the div with class contents inside it
            contents_div = second_listing.find('div', class_='contents')
            
            if contents_div:
                print("Found contents div")
                
                # Find all divs with class search-result inside contents
                search_results = contents_div.find_all('div', class_='search-result')
                print(f"Found {len(search_results)} search-result divs")
                
                # Loop through each search-result div
                for idx, result in enumerate(search_results):
                    print(f"\n--- Result {idx + 1} ---")
                    
                    # Find the div with class search-result-meta
                    meta_div = result.find('div', class_='search-result-meta')
                    
                    if meta_div:
                        # Find span with no class name that contains an <a> tag
                        span = meta_div.find('span', class_=False)
                        
                        if span:
                            # Find the <a> tag inside the span
                            link = span.find('a')
                            
                            if link:
                                # Extract text from the <a> tag (subreddit name)
                                link_text = link.get_text(strip=True)
                                print(f"Subreddit: {link_text}")
                                anchor_texts.add(link_text)
            else:
                print("Contents div not found")
        else:
            print("Second search-result-listing div not found")
        
        print(f"\n\n=== All subreddits found ({len(anchor_texts)} total) ===")
        for text in anchor_texts:
            print(text)
        
        return list(anchor_texts)
    
    except Exception as e:
        print(f"Error fetching the page: {e}")
        return []