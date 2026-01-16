import re
from typing import List


def format_posts_for_llm(posts: list) -> str:
    """Format a list of posts into XML-like structure for LLM processing."""
    batch_str = "<batch>\n"
    
    for p in posts:
        clean_content = minify_text(p['text'])
        
        batch_str += (
            f'  <post id="{p["id"]}">\n'
            f'    <url>{p["url"]}</url>\n'
            f'    <content>{clean_content}</content>\n'
            f'  </post>\n'
        )
        
    batch_str += "</batch>"
    return batch_str


def format_entity_names_for_resolution(canonical_names: List[str]) -> str:
    """Format a list of entity names into XML-like structure for entity resolution."""
    prompt_str = (
        "Here is a list of unique entity names extracted from news logs. "
        "Group those that refer to the same real-world entity and provide a single master name for each group.\n\n"
        "<entities>\n"
    )
    
    for name in canonical_names:
        prompt_str += f"  <entity>{name}</entity>\n"
    
    prompt_str += "</entities>"
    return prompt_str


def minify_text(text: str) -> str:
    """Clean and minify text by removing emojis and normalizing whitespace."""
    if not text:
        return ""
    
    # 1. Remove Emojis (removes all non-BMP characters)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # 2. Normalize Whitespace & Newlines
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
