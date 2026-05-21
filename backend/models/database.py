import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data")) / "feeds.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                items_json TEXT NOT NULL,
                title_selector TEXT,
                link_selector TEXT,
                description_selector TEXT,
                image_selector TEXT,
                native_rss_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def create_feed(
    source_url: str,
    title: str,
    items: list[dict],
    native_rss_url: str | None = None,
    title_selector: str | None = None,
    link_selector: str | None = None,
    description_selector: str | None = None,
    image_selector: str | None = None,
) -> str:
    feed_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO feeds (
                id, source_url, title, items_json,
                title_selector, link_selector, description_selector, image_selector,
                native_rss_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feed_id, source_url, title, json.dumps(items, ensure_ascii=False),
                title_selector, link_selector, description_selector, image_selector,
                native_rss_url, now, now,
            ),
        )
        conn.commit()

    return feed_id


def get_feed(feed_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def update_feed_items(feed_id: str, items: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE feeds SET items_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(items, ensure_ascii=False), now, feed_id),
        )
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "source_url": row["source_url"],
        "title": row["title"],
        "items": json.loads(row["items_json"]),
        "title_selector": row["title_selector"],
        "link_selector": row["link_selector"],
        "description_selector": row["description_selector"],
        "image_selector": row["image_selector"],
        "native_rss_url": row["native_rss_url"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
