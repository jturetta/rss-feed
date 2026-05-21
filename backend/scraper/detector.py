from urllib.parse import urljoin

from bs4 import BeautifulSoup


def detect_native_rss(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")

    for link in soup.find_all("link", rel="alternate"):
        type_ = link.get("type", "")
        if "rss" in type_ or "atom" in type_ or "xml" in type_:
            href = link.get("href")
            if href:
                return urljoin(base_url, href)

    return None
