import os
import socket
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from models.database import create_feed, get_feed, init_db, update_feed_items
from rss.generator import build_rss
from scraper.detector import detect_native_rss
from scraper.extractor import extract_items_heuristic, extract_with_selectors
from scraper.fetcher import fetch_page

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="RSS Feed Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PreviewRequest(BaseModel):
    url: HttpUrl
    title_selector: str | None = None
    link_selector: str | None = None
    description_selector: str | None = None
    image_selector: str | None = None


class CreateFeedRequest(PreviewRequest):
    title: str | None = None


@app.on_event("startup")
def startup() -> None:
    init_db()


def _get_lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


@app.get("/api/server-info")
def server_info():
    port = int(os.environ.get("PORT", "8000"))
    return {"lan_ip": _get_lan_ip(), "port": port}


@app.get("/health")
def health():
    return {"status": "ok"}


async def _extract_from_url(req: PreviewRequest) -> dict:
    url = str(req.url)
    html, final_url = await fetch_page(url)

    native = detect_native_rss(html, final_url)
    if native:
        return {
            "type": "native",
            "source_url": final_url,
            "native_rss_url": native,
            "items": [],
            "items_count": 0,
        }

    if req.title_selector and req.link_selector:
        items = extract_with_selectors(
            html,
            final_url,
            req.title_selector,
            req.link_selector,
            req.description_selector,
            req.image_selector,
        )
    else:
        items = extract_items_heuristic(html, final_url)

    if not items:
        raise HTTPException(
            422,
            "Não foi possível extrair itens desta página. Tente seletores CSS personalizados.",
        )

    return {
        "type": "generated",
        "source_url": final_url,
        "items": items,
        "items_count": len(items),
    }


@app.post("/api/preview")
async def preview_feed(req: PreviewRequest):
    return await _extract_from_url(req)


@app.post("/api/feeds")
async def save_feed(req: CreateFeedRequest):
    result = await _extract_from_url(req)

    if result["type"] == "native":
        feed_id = create_feed(
            source_url=result["source_url"],
            title=req.title or result["source_url"],
            items=[],
            native_rss_url=result["native_rss_url"],
        )
        return {
            "type": "native",
            "feed_id": feed_id,
            "native_rss_url": result["native_rss_url"],
            "feed_url": result["native_rss_url"],
        }

    feed_id = create_feed(
        source_url=result["source_url"],
        title=req.title or result["source_url"],
        items=result["items"],
        title_selector=req.title_selector,
        link_selector=req.link_selector,
        description_selector=req.description_selector,
        image_selector=req.image_selector,
    )

    return {
        "type": "generated",
        "feed_id": feed_id,
        "feed_url": f"/feed/{feed_id}.xml",
        "items_count": result["items_count"],
    }


@app.get("/api/feeds/{feed_id}")
async def feed_info(feed_id: str):
    feed = get_feed(feed_id)
    if not feed:
        raise HTTPException(404, "Feed não encontrado")
    return feed


@app.get("/feed/{feed_id}.xml")
async def serve_feed(feed_id: str, request: Request):
    feed = get_feed(feed_id)
    if not feed:
        raise HTTPException(404, "Feed não encontrado")

    if feed["native_rss_url"]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(feed["native_rss_url"])
            resp.raise_for_status()
            return Response(content=resp.content, media_type="application/rss+xml")

    try:
        html, final_url = await fetch_page(feed["source_url"])
        if feed["title_selector"] and feed["link_selector"]:
            items = extract_with_selectors(
                html,
                final_url,
                feed["title_selector"],
                feed["link_selector"],
                feed["description_selector"],
                feed["image_selector"],
            )
        else:
            items = extract_items_heuristic(html, final_url)
        if items:
            update_feed_items(feed_id, items)
            feed["items"] = items
    except Exception:
        pass

    feed_url = str(request.url)
    xml = build_rss(
        feed["title"],
        feed_url,
        feed["source_url"],
        feed["items"],
    )
    return Response(content=xml, media_type="application/rss+xml")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
