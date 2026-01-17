"""Subreddit ranking via search result scraping."""

from bs4 import BeautifulSoup, Tag
from typing import List, Optional
from curl_cffi import requests

from .constants import SUBREDDIT_SEARCH_TEMPLATE
from .helpers import get_random_impersonate_target
from .models import SubredditPost


def _extract_post_id(result: Tag) -> str:
    """Extract post ID from data-fullname attribute."""
    post_id = result.get('data-fullname', '')
    return post_id


def _extract_post_title_and_url(result: Tag) -> SubredditPost:
    """Extract post title and URL from the result element."""
    data = SubredditPost()
    
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
                data.post_url = post_url or ""
                
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
                data.post_title = post_title or ""
    
    return data


def _extract_metadata(result: Tag) -> SubredditPost:
    """Extract upvotes, comments count, and created datetime from metadata div."""
    data = SubredditPost()
    
    meta_div = result.find('div', class_='search-result-meta')
    if not meta_div:
        return data
    
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
        data.ups = upvotes_num
    
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
        data.num_comments = num_comments
    
    # Extract created_datetime from time tag
    time_span = meta_div.find('span', class_='search-time')
    if time_span:
        time_tag = time_span.find('time')
        if time_tag:
            created_datetime = time_tag.get('datetime', '')
            data.created_datetime = created_datetime or ""
    
    return data


def _extract_self_text(result: Tag) -> Optional[str]:
    """Extract self text from the expando div."""
    expando_div = result.find('div', class_='search-expando')
    if expando_div:
        body_div = expando_div.find('div', class_='search-result-body')
        if body_div:
            paragraphs = body_div.find_all('p')
            self_text_parts = [p.get_text(strip=True) for p in paragraphs]
            self_text = ' '.join(self_text_parts)
            return self_text
    return None


def _parse_search_result(result: Tag, idx: int) -> SubredditPost:
    """Parse a single search result element into a SubredditPost."""

    result_data = SubredditPost(post_id=_extract_post_id(result))

    # Extract post title and URL
    title_url_data = _extract_post_title_and_url(result)

    # Extract metadata (upvotes, comments, datetime)
    metadata = _extract_metadata(result)

    # Extract self text
    self_text = _extract_self_text(result)

    update_data = {
        **title_url_data.model_dump(exclude_defaults=True),
        **metadata.model_dump(exclude_defaults=True),
    }
    if self_text:
        update_data["self_text"] = self_text

    result_data = result_data.model_copy(update=update_data)

    return result_data


def _parse_search_results_from_listing(listing: Tag) -> List[SubredditPost]:
    """Parse all search results from a listing div."""
    results: List[SubredditPost] = []
    
    # Find the div with class contents inside it
    contents_div = listing.find('div', class_='contents')
    
    if not contents_div:
        return results
    
    # Find all divs with class search-result inside contents
    search_results = contents_div.find_all('div', class_='search-result')
    
    # Loop through each search-result div
    for idx, result in enumerate(search_results):
        result_data = _parse_search_result(result, idx)
        results.append(result_data)
    
    return results


def _fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch a page and return parsed BeautifulSoup object."""
    # Select random impersonate target for browser mimicking
    impersonate_target = get_random_impersonate_target()
    
    # Fetch the page with curl_cffi for browser impersonation
    response = requests.get(url, impersonate=impersonate_target, timeout=10)
    response.raise_for_status()
    
    
    # Parse with Beautiful Soup
    return BeautifulSoup(response.content, 'lxml')


def scrape_subreddit_search_page(soup: BeautifulSoup) -> List[SubredditPost]:
    """
    Scrape a single page of subreddit search results from a BeautifulSoup object.
    
    Args:
        soup: Parsed HTML for the subreddit search page
        
    Returns:
        List containing results
    """
    try:
        # Find all divs with class search-result-listing
        search_listing_divs = soup.find_all('div', class_='search-result-listing')

        # Get the first one (index 0)
        if len(search_listing_divs) > 0:
            first_listing = search_listing_divs[0]
            return _parse_search_results_from_listing(first_listing)
        else:
            return []

    except Exception as e:
        print(f"Error parsing the page: {e}")
        return []


def get_relevant_posts_from_subreddit(subreddit: str, query: str) -> List[SubredditPost]:
    """
    Scrape subreddit search results with a single page request.
    
    Args:
        subreddit: The subreddit name to search in (e.g., 'OpenAI')
        query: The search query (e.g., 'openai')
        
    Returns:
        List of all results from all pages
    """
    # Build the URL from template
    url = SUBREDDIT_SEARCH_TEMPLATE.format(subreddit=subreddit, query=query)
    
    print(f"Scraping URL: {url}")

    soup = _fetch_page(url)
    if not soup:
        return []

    page_results = scrape_subreddit_search_page(soup)

    print(f"Scrape complete. Results: {len(page_results)}")

    return page_results


def test_get_relevant_posts_from_subreddit(file_path: str) -> List[SubredditPost]:
    """
    Test helper to parse subreddit search results from a local HTML file.

    Args:
        file_path: Path to a local HTML file containing search results

    Returns:
        List of parsed posts
    """
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            html = handle.read()
        soup = BeautifulSoup(html, "lxml")
        return scrape_subreddit_search_page(soup)
    except Exception as exc:
        print(f"Failed to parse local HTML: {exc}")
        return []
