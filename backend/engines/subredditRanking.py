import requests
from bs4 import BeautifulSoup
from typing import List, Dict

# Template URL for subreddit search
SUBREDDIT_SEARCH_TEMPLATE = "https://old.reddit.com/r/{subreddit}/search/?q={query}&include_over_18=on&restrict_sr=on&t=month&sort=relevance"

# Headers to mimic a browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def scrape_subreddit_search_page(url: str) -> tuple[List[Dict], str | None]:
    """
    Scrape a single page of subreddit search results.
    
    Args:
        url: The subreddit search URL to scrape
        
    Returns:
        Tuple containing list of results and next page URL (or None if no more pages)
    """
    try:
        # Fetch the page
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        print(f"Response Code: {response.status_code}")
        
        # Parse with Beautiful Soup
        soup = BeautifulSoup(response.content, 'lxml')
        
        results = []
        
        # Find all divs with class search-result-listing
        search_listing_divs = soup.find_all('div', class_='search-result-listing')
        print(f"Found {len(search_listing_divs)} search-result-listing divs")
        
        # Get the first one (index 0)
        if len(search_listing_divs) > 0:
            first_listing = search_listing_divs[0]
            print("Found first search-result-listing div")
            
            # Find the div with class contents inside it
            contents_div = first_listing.find('div', class_='contents')
            
            if contents_div:
                print("Found contents div")
                
                # Find all divs with class search-result inside contents
                search_results = contents_div.find_all('div', class_='search-result')
                print(f"Found {len(search_results)} search-result divs")
                
                # Loop through each search-result div
                for idx, result in enumerate(search_results):
                    print(f"\n--- Result {idx + 1} ---")
                    
                    result_data = {}
                    
                    # Extract post id from data-fullname attribute
                    post_id = result.get('data-fullname', '')
                    result_data['post_id'] = post_id
                    print(f"Post ID: {post_id}")
                    
                    # === Extract post title and url ===
                    # Find classless div within search-result
                    classless_div = result.find('div', class_=False)
                    
                    if classless_div:
                        # Find header
                        header = classless_div.find('header')
                        
                        if header:
                            # Find the <a> tag
                            link = header.find('a')
                            
                            if link:
                                # Extract post url (href)
                                post_url = link.get('href', '')
                                result_data['post_url'] = post_url
                                print(f"Post URL: {post_url}")
                                
                                # Extract post title (combine mark tag and plain text)
                                title_parts = []
                                for child in link.children:
                                    if child.name == 'mark':
                                        title_parts.append(child.get_text(strip=True))
                                    elif isinstance(child, str):
                                        text = child.strip()
                                        if text:
                                            title_parts.append(text)
                                
                                post_title = ''.join(title_parts)
                                result_data['post_title'] = post_title
                                print(f"Post Title: {post_title}")
                    
                    # === Extract upvotes and other metadata ===
                    meta_div = result.find('div', class_='search-result-meta')
                    if meta_div:
                        # Extract upvotes
                        score_span = meta_div.find('span', class_='search-score')
                        if score_span:
                            upvotes_text = score_span.get_text(strip=True)
                            # Extract number from "1,243 points" format
                            upvotes_num_str = upvotes_text.split()[0].replace(',', '') if upvotes_text else '0'
                            try:
                                upvotes_num = int(upvotes_num_str)
                            except ValueError:
                                upvotes_num = 0
                            result_data['ups'] = upvotes_num
                            print(f"Upvotes: {upvotes_num}")
                        
                        # Extract num_comments from search-comments link
                        comments_link = meta_div.find('a', class_='search-comments')
                        if comments_link:
                            comments_text = comments_link.get_text(strip=True)
                            # Extract number from "1,243 comments" format
                            num_comments_str = comments_text.split()[0].replace(',', '') if comments_text else '0'
                            try:
                                num_comments = int(num_comments_str)
                            except ValueError:
                                num_comments = 0
                            result_data['num_comments'] = num_comments
                            print(f"Comments: {num_comments}")
                        
                        # Extract created_datetime from time tag
                        time_span = meta_div.find('span', class_='search-time')
                        if time_span:
                            time_tag = time_span.find('time')
                            if time_tag:
                                created_datetime = time_tag.get('datetime', '')
                                result_data['created_datetime'] = created_datetime
                                print(f"Created: {created_datetime}")
                    
                    # === Extract self_text ===
                    expando_div = result.find('div', class_='search-expando')
                    if expando_div:
                        body_div = expando_div.find('div', class_='search-result-body')
                        if body_div:
                            paragraphs = body_div.find_all('p')
                            self_text_parts = [p.get_text(strip=True) for p in paragraphs]
                            self_text = ' '.join(self_text_parts)
                            result_data['self_text'] = self_text
                            print(f"Self Text: {self_text[:100]}..." if len(self_text) > 100 else f"Self Text: {self_text}")
                    
                    results.append(result_data)
                    print(f"Result data: {result_data}")
                
                # === Extract next page link ===
                # Find footer in search-result-listing
                footer = first_listing.find('footer')
                next_url = None
                
                if footer:
                    # Find span with class nextprev
                    nextprev_span = footer.find('span', class_='nextprev')
                    if nextprev_span:
                        # Find all <a> tags and get the last one
                        links = nextprev_span.find_all('a')
                        if links:
                            last_link = links[-1]
                            next_url = last_link.get('href', None)
                            if next_url:
                                # Handle relative URLs
                                if next_url.startswith('/'):
                                    next_url = 'https://old.reddit.com' + next_url
                                elif not next_url.startswith('http'):
                                    next_url = 'https://old.reddit.com/' + next_url
                            print(f"\nNext page URL: {next_url}")
                else:
                    print("Footer not found")
                
                return results, next_url
            else:
                print("Contents div not found")
                return results, None
        else:
            print("First search-result-listing div not found")
            return results, None
    
    except Exception as e:
        print(f"Error fetching the page: {e}")
        return [], None


def scrape_subreddit_search(subreddit: str, query: str, max_pages: int = None) -> List[Dict]:
    """
    Scrape subreddit search results with pagination support.
    
    Args:
        subreddit: The subreddit name to search in (e.g., 'OpenAI')
        query: The search query (e.g., 'openai')
        max_pages: Maximum number of pages to scrape (None for all pages)
        
    Returns:
        List of all results from all pages
    """
    # Build the URL from template
    url = SUBREDDIT_SEARCH_TEMPLATE.format(subreddit=subreddit, query=query)
    
    all_results = []
    current_url = url
    page_count = 0
    
    while current_url and (max_pages is None or page_count < max_pages):
        page_count += 1
        print(f"\n\n========== Scraping Page {page_count} ==========")
        print(f"URL: {current_url}")
        
        page_results, next_url = scrape_subreddit_search_page(current_url)
        all_results.extend(page_results)
        current_url = next_url
    
    print(f"\n\n=== Scraping Complete ===")
    print(f"Total pages scraped: {page_count}")
    print(f"Total results: {len(all_results)}")
    
    return all_results
