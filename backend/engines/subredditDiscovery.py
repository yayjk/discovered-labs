import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time

# Reddit search URL template
REDDIT_SEARCH_TEMPLATE = "https://old.reddit.com/search/?q={query}&sort=relevance&t=week"

# Headers to mimic a browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def scrape_reddit_search(query: str) -> List[str]:
    """
    Scrape Reddit search results using Beautiful Soup.
    
    Args:
        query: The search query (e.g., 'openai')
        
    Returns:
        List of subreddit names found in the search results
    """
    # Build the URL from template
    url = REDDIT_SEARCH_TEMPLATE.format(query=query)
    
    try:
        # Fetch the page
        response = requests.get(url, headers=HEADERS, timeout=10)
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