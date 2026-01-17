"""Prompts for LLM-based discovery."""


def get_subreddit_finder_prompt(topic: str) -> str:
    """
    Get the prompt for finding subreddits via LLM.
    
    Args:
        topic: The topic to find subreddits for
        
    Returns:
        The formatted prompt string
    """
    return (
        f"Identify the 10 most active and relevant subreddits for the topic: '{topic}'. "
        "Focus on communities where users discuss breaking updates, latest news, or current events. "
        "Return the data as a JSON object with a list of 'subreddits', each containing 'name' (with r/)."
    )
