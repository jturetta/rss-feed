import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Padrões comuns de URL de artigo
_ARTICLE_URL_RE = re.compile(
    r"/(?:noticias|news|blog|posts?|artigos?)/[^/?#]+(?:-\d+)?/?$",
    re.I,
)

# Títulos típicos de navegação/seção que devem ser ignorados
_NAV_TITLES = {
    "dividendos", "aprendizagem", "ferramentas", "mais buscados", "setores",
    "rankings", "nacional", "internacional", "conteúdo", "cursos", "mercado",
    "economia", "negócios", "política", "internacional", "criptomoedas",
    "ver todos", "ver mais", "começar", "entrar", "cadastre-se",
}


def extract_items_heuristic(html: str, base_url: str, limit: int = 30) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    for strategy in (
        _extract_from_link_cards,
        _extract_from_articles,
        _extract_from_news_urls,
        _extract_from_generic_containers,
    ):
        items = strategy(soup, base_url, limit)
        if len(items) >= 3:
            return items

    return items[:limit]


def extract_with_selectors(
    html: str,
    base_url: str,
    title_selector: str,
    link_selector: str,
    description_selector: str | None = None,
    image_selector: str | None = None,
    limit: int = 30,
) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    seen: set[str] = set()

    title_els = soup.select(title_selector)
    link_els = soup.select(link_selector)

    for i, title_el in enumerate(title_els):
        title = title_el.get_text(strip=True)
        if not title or _is_nav_title(title):
            continue

        link = ""
        if i < len(link_els):
            link_el = link_els[i]
            if link_el.name == "a" and link_el.get("href"):
                link = urljoin(base_url, link_el["href"])
            else:
                anchor = link_el.find("a", href=True) or link_el.find_parent("a", href=True)
                if anchor:
                    link = urljoin(base_url, anchor["href"])

        if not link or link in seen:
            continue
        seen.add(link)

        description = ""
        if description_selector:
            desc_els = soup.select(description_selector)
            if i < len(desc_els):
                description = desc_els[i].get_text(strip=True)

        image = _extract_image(title_el, base_url, image_selector, i, soup)

        items.append({"title": title, "link": link, "description": description, "image": image})

    return items[:limit]


def _extract_from_link_cards(soup: BeautifulSoup, base_url: str, limit: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    for card in soup.select('a.link-card, a[class*="link-card"], .news-container a[href]'):
        item = _extract_from_card(card, base_url)
        if item and item["link"] not in seen:
            seen.add(item["link"])
            items.append(item)

    return items[:limit]


def _extract_from_articles(soup: BeautifulSoup, base_url: str, limit: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    for el in soup.find_all("article"):
        item = _extract_from_element(el, base_url)
        if item and item["link"] not in seen:
            seen.add(item["link"])
            items.append(item)

    return items[:limit]


def _extract_from_news_urls(soup: BeautifulSoup, base_url: str, limit: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    base_host = urlparse(base_url).netloc

    for anchor in soup.find_all("a", href=True):
        link = urljoin(base_url, anchor["href"])
        if link in seen or urlparse(link).netloc != base_host:
            continue
        if not _looks_like_article_url(link, base_url):
            continue

        title = _find_title_near(anchor)
        if not title or _is_nav_title(title) or len(title) < 15:
            continue

        seen.add(link)
        parent = anchor if anchor.name == "a" else anchor.find_parent("a")
        img = parent.find("img") if parent else anchor.find("img")
        image = _img_src(img, base_url)

        desc_el = anchor.find("p") or (anchor.parent and anchor.parent.find("p"))
        description = desc_el.get_text(strip=True) if desc_el else ""

        items.append({"title": title, "link": link, "description": description, "image": image})

    return items[:limit]


def _extract_from_generic_containers(soup: BeautifulSoup, base_url: str, limit: int) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    for el in soup.find_all(["div", "li", "section"], class_=True):
        if _is_likely_nav(el):
            continue
        item = _extract_from_element(el, base_url)
        if item and item["link"] not in seen and not _is_nav_title(item["title"]):
            seen.add(item["link"])
            items.append(item)

    return items[:limit]


def _extract_from_card(card, base_url: str) -> dict | None:
    href = card.get("href")
    if not href:
        return None

    link = urljoin(base_url, href)
    if not link.startswith("http"):
        return None

    title_el = card.select_one("h1, h2, h3, h4, .title")
    if not title_el:
        return None

    title = title_el.get_text(strip=True)
    if not title or _is_nav_title(title):
        return None

    desc_el = card.select_one("p.intro, p.excerpt, p.description, p.summary, p")
    description = desc_el.get_text(strip=True) if desc_el else ""

    img = card.select_one("img")
    image = _img_src(img, base_url)

    return {"title": title, "link": link, "description": description, "image": image}


def _extract_from_element(el, base_url: str) -> dict | None:
    link_el = el.find("a", href=True)
    title_el = el.find(["h1", "h2", "h3", "h4"])
    if not link_el or not title_el:
        return None

    title = title_el.get_text(strip=True)
    if not title or _is_nav_title(title):
        return None

    link = urljoin(base_url, link_el["href"])
    if not link.startswith("http"):
        return None

    img = el.find("img")
    desc_el = el.find("p")

    return {
        "title": title,
        "link": link,
        "description": desc_el.get_text(strip=True) if desc_el else "",
        "image": _img_src(img, base_url),
    }


def _find_title_near(anchor) -> str:
    title_el = anchor.select_one("h1, h2, h3, h4, .title")
    if title_el:
        return title_el.get_text(strip=True)

    parent = anchor.parent
    for _ in range(3):
        if not parent:
            break
        title_el = parent.find(["h1", "h2", "h3", "h4"])
        if title_el:
            return title_el.get_text(strip=True)
        parent = parent.parent

    text = anchor.get_text(strip=True)
    text = re.sub(r"^\d+", "", text).strip()
    return text


def _looks_like_article_url(link: str, base_url: str) -> bool:
    if _ARTICLE_URL_RE.search(link):
        return True

    path = urlparse(link).path.rstrip("/")
    base_path = urlparse(base_url).path.rstrip("/")

    # URL filha do path base com slug longo (ex: /noticias/titulo-da-materia-12345)
    if base_path and path.startswith(base_path) and path != base_path:
        slug = path[len(base_path):].strip("/")
        return len(slug) > 10 and slug.count("-") >= 2

    return False


def _is_nav_title(title: str) -> bool:
    normalized = title.strip().lower()
    if normalized in _NAV_TITLES:
        return True
    if len(normalized) < 20 and normalized.split()[0] in _NAV_TITLES:
        return True
    return False


def _is_likely_nav(el) -> bool:
    classes = " ".join(el.get("class", [])).lower()
    nav_hints = ("menu", "nav", "header", "footer", "sidebar", "dropdown", "toolbar")
    return any(h in classes for h in nav_hints)


def _img_src(img, base_url: str) -> str | None:
    if not img:
        return None
    src = img.get("src") or img.get("data-src")
    if src and not src.startswith("data:"):
        return urljoin(base_url, src)
    return None


def _extract_image(title_el, base_url: str, image_selector: str | None, index: int, soup) -> str | None:
    if image_selector:
        img_els = soup.select(image_selector)
        if index < len(img_els):
            return _img_src(img_els[index], base_url)

    parent = title_el.find_parent("a") or title_el.parent
    if parent:
        return _img_src(parent.find("img"), base_url)
    return None
