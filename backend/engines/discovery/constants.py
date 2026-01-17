"""Constants for the discovery module."""

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

# URL Templates
REDDIT_SEARCH_TEMPLATE = "https://old.reddit.com/search/?q={query}&sort=relevance&t=week"
SUBREDDIT_SEARCH_TEMPLATE = "https://old.reddit.com/r/{subreddit}/search/?q={query}&include_over_18=on&restrict_sr=on&t=month&sort=relevance&limit=100"
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
