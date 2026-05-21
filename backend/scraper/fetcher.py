import httpx

USER_AGENT = "RSSFeedBot/1.0 (+https://github.com/rss-feed-generator)"


async def fetch_page(url: str) -> tuple[str, str]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return resp.text, str(resp.url)
