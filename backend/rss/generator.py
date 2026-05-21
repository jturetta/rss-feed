from datetime import datetime, timezone

from feedgen.feed import FeedGenerator


def build_rss(feed_title: str, feed_url: str, site_url: str, items: list[dict]) -> str:
    fg = FeedGenerator()
    fg.title(feed_title)
    fg.link(href=site_url, rel="alternate")
    fg.description(f"Feed gerado automaticamente de {site_url}")
    fg.language("pt-BR")

    for item in items:
        fe = fg.add_entry()
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.guid(item["link"], permalink=True)
        if item.get("description"):
            fe.description(item["description"])
        if item.get("image"):
            fe.enclosure(item["image"], 0, "image/jpeg")
        fe.pubDate(datetime.now(timezone.utc))

    return fg.rss_str(pretty=True).decode("utf-8")
