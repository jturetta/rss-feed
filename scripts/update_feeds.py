#!/usr/bin/env python3
"""Atualiza os arquivos RSS em docs/feeds/ a partir de feeds.json."""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from rss.generator import build_rss
from scraper.detector import detect_native_rss
from scraper.extractor import extract_items_heuristic, extract_with_selectors
from scraper.fetcher import fetch_page

FEEDS_JSON = ROOT / "feeds.json"
OUTPUT_DIR = ROOT / "docs" / "feeds"
DOCS_INDEX = ROOT / "docs" / "index.html"


async def process_feed(feed: dict, pages_base_url: str) -> tuple[str, str] | None:
    source_url = feed["source_url"]
    html, final_url = await fetch_page(source_url)

    native = detect_native_rss(html, final_url)
    if native:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(native)
            resp.raise_for_status()
            return feed["id"], resp.text

    if feed.get("title_selector") and feed.get("link_selector"):
        items = extract_with_selectors(
            html,
            final_url,
            feed["title_selector"],
            feed["link_selector"],
            feed.get("description_selector"),
            feed.get("image_selector"),
        )
    else:
        items = extract_items_heuristic(html, final_url)

    if not items:
        print(f"  AVISO: nenhum item em {source_url}")
        return None

    feed_url = f"{pages_base_url.rstrip('/')}/feeds/{feed['id']}.xml"
    xml = build_rss(feed.get("title") or source_url, feed_url, final_url, items)
    return feed["id"], xml


def _pages_base_url() -> str:
    env_url = os.environ.get("PAGES_BASE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}"

    return "https://SEU-USUARIO.github.io/rss-feed"


def _write_index(feeds: list[dict], pages_base_url: str) -> None:
    items_html = "\n".join(
        f'        <li><a href="feeds/{f["id"]}.xml">{f.get("title", f["id"])}</a>'
        f' <span class="feed-url">{pages_base_url}/feeds/{f["id"]}.xml</span></li>'
        for f in feeds
        if f.get("id")
    )
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RSS Feed Generator</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>RSS Feed Generator</h1>
      <p class="subtitle">Feeds RSS públicos — atualizados a cada 6h via GitHub Actions</p>
    </header>
    <section class="card">
      <h2>Feeds disponíveis</h2>
      <ul class="feed-list">
{items_html}
      </ul>
    </section>
  </div>
</body>
</html>
"""
    DOCS_INDEX.write_text(html, encoding="utf-8")


async def main() -> None:
    pages_base_url = _pages_base_url()
    config = json.loads(FEEDS_JSON.read_text(encoding="utf-8"))
    feeds = config.get("feeds", [])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Atualizando {len(feeds)} feed(s) → {OUTPUT_DIR}")
    print(f"URL base: {pages_base_url}")

    for feed in feeds:
        feed_id = feed.get("id")
        if not feed_id:
            print("  ERRO: feed sem id, ignorado")
            continue

        print(f"  → {feed_id} ({feed['source_url']})")
        try:
            result = await process_feed(feed, pages_base_url)
            if result:
                fid, xml = result
                (OUTPUT_DIR / f"{fid}.xml").write_text(xml, encoding="utf-8")
                print(f"    OK: {fid}.xml")
        except Exception as exc:
            print(f"    ERRO: {exc}")

    _write_index(feeds, pages_base_url)
    print("  OK: docs/index.html")


if __name__ == "__main__":
    asyncio.run(main())
