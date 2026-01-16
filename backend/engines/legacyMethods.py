def find_subreddits_via_reddit_posts_search(query: str, min_comments: int = 10) -> dict:
    """Fetch posts from `search query` and return a dict mapping `subreddit_name_prefixed` -> `subreddit_subscribers`.

    Rules:
    - Skip posts where `num_comments` is less than `min_comments`.
    - If a subreddit is already added, skip subsequent posts from the same subreddit.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    url="https://www.reddit.com/search.json?q={query}&sort=relevance&t=month&limit=25"

    try:
        resp = curl_requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch posts from Reddit: {exc}") from exc

    results: list = []

    for i, child in enumerate(payload.get("data", {}).get("children", [])):
        if not isinstance(child, dict):
            continue
        data = child.get("data", {})

        # Get subreddit identifier
        subreddit_prefixed = data.get("subreddit_name_prefixed")

        # Skip low-engagement posts
        try:
            num_comments = int(data.get("num_comments", 0))
        except (TypeError, ValueError):
            continue
        if num_comments < min_comments:
            continue

        if subreddit_prefixed and subreddit_prefixed not in results:
            results.append(subreddit_prefixed)

    return results


async def calculate_and_insert_subreddit_score(db_conn, subreddit: str, subs: int, query: str, timeout: int, now: float):
    """Async method to calculate scores for a subreddit and insert into DB."""
    try:
        frequency = 0
        total_votes = 0
        total_comments = 0
        vote_counted_posts = 0
        freshness = 0
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"}

        # Use a single search call per subreddit to compute frequency, freshness, and engagement
        search_url = f"https://www.reddit.com/{subreddit}/search.json"
        params = {"q": query, "sort": "new", "restrict_sr": "1", "limit": 100}
        async with AsyncSession() as client:
            resp_search = await client.get(search_url, headers=headers, params=params, timeout=timeout)
            if resp_search.status_code == 200:
                json_response = resp_search.text  # Store the raw JSON response
                posts = resp_search.json().get("data", {}).get("children", [])
                q_lower = (query or "").lower()
                pattern = re.compile(re.escape(q_lower))
                cutoff = now - (48 * 3600)
                for p in posts:
                    data = p.get("data", {})
                    title_lower = (data.get("title") or "").lower()
                    selftext_lower = (data.get("selftext") or "").lower()
                    text = title_lower + " " + selftext_lower

                    # Frequency: count occurrences of query in title+selftext
                    frequency += len(pattern.findall(text))

                    # Votes for engagement
                    ups = data.get("ups") or 0
                    downs = data.get("downs") or 0
                    num_comments = data.get("num_comments") or 0
                    try:
                        total_votes += int(ups) + abs(int(downs))
                        total_comments += int(num_comments)
                        vote_counted_posts += 1
                    except Exception:
                        pass

                    # Freshness: posts in last 48 hours
                    created = data.get("created_utc")
                    try:
                        if created and float(created) >= cutoff:
                            freshness += 1
                    except Exception:
                        pass
            else:
                print(f"Failed to fetch posts for {subreddit}, status code: {resp_search.status_code}")
                json_response = None

        engagement_raw = ((total_votes + total_comments) / subs) * 1000 if subs and subs > 0 else 0

        print(f"Subreddit: {subreddit}, Subs: {subs}, Freq: {frequency}, Fresh: {freshness}, Eng: {engagement_raw:.2f}")
        # Insert into DB
        await insert_subreddit(db_conn, subreddit, json_response, engagement_raw, freshness, frequency, subs)

    except Exception as e:
        print(f"Error processing {subreddit}: {e}")