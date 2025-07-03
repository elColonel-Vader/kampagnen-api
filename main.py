from fastapi import FastAPI, Query
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
from fastapi.middleware.gzip import GZipMiddleware
import re

app = FastAPI()

# Add transparent gzip compression for large responses (>1 kB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# regex patterns for color extraction (hex and rgb/rgba)
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,6}\b")
RGB_COLOR_RE = re.compile(r"rgba?\([^)]*\)")

class AnalyzeResponse(BaseModel):
    url: str
    title: str
    text: str
    images: List[str]
    logos: List[str]
    colors: List[str]
    crawled_pages: int

# Hilfsfunktion zur Prüfung auf gleiche Domain
def is_same_domain(base: str, target: str) -> bool:
    return urlparse(base).netloc == urlparse(target).netloc

@app.get("/crawl-analyze", response_model=AnalyzeResponse)
def crawl_analyze(
    url: str = Query(...),
    max_pages: int = Query(5, description="Maximale Anzahl an Seiten"),
    min_images: int = Query(10, description="Minimale Anzahl an Bildern"),
    max_images: int = Query(20, description="Maximal zurückzugebende Bilder"),
    max_logos: int = Query(5, description="Maximal zurückzugebende Logos"),
    max_colors: int = Query(10, description="Maximal zurückzugebende Farbcodes"),
    max_text_chars: int = Query(10000, description="Maximale Länge des extrahierten Textes (Zeichen)")
):
    visited: Set[str] = set()
    to_visit: List[str] = [url]
    all_images: Set[str] = set()
    logos_set: Set[str] = set()
    colors_set: Set[str] = set()
    full_text = ""
    final_title = ""
    crawled_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            java_script_enabled=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            try:
                page.goto(current_url, timeout=30000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string.strip() if soup.title else ""
                text = soup.get_text(" ", strip=True)
                if not final_title:
                    final_title = title
                full_text += " " + text

                for tag in soup.find_all(["img", "meta", "link", "source"]):
                    src = tag.get("src") or tag.get("content") or tag.get("href") or tag.get("srcset")
                    if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".svg"]):
                        abs_src = urljoin(current_url, src)
                        all_images.add(abs_src)
                        # basic logo heuristics
                        alt_text = (tag.get("alt") or "").lower()
                        class_text = " ".join(tag.get("class", [])) if tag.has_attr("class") else ""
                        if "logo" in src.lower() or "logo" in alt_text or "logo" in class_text.lower():
                            logos_set.add(abs_src)

                for link in soup.find_all("a", href=True):
                    href = urljoin(current_url, link["href"])
                    if is_same_domain(url, href) and href not in visited and href not in to_visit:
                        to_visit.append(href)

                # extract color codes from raw HTML (includes inline styles & style blocks)
                colors_found = HEX_COLOR_RE.findall(html) + RGB_COLOR_RE.findall(html)
                for c in colors_found:
                    colors_set.add(c.lower())

                visited.add(current_url)
                crawled_count += 1
            except Exception as e:
                print(f"Fehler bei {current_url}: {e}")
                continue

        browser.close()

    while len(all_images) < min_images:
        all_images.add("https://via.placeholder.com/600x400?text=Platzhalter")

    # Apply "light" slicing
    images_list = list(all_images)[:max_images]
    logos_list = list(logos_set)[:max_logos]
    colors_list = list(colors_set)[:max_colors]

    full_text = full_text.strip()
    # Truncate text to mitigate overly large JSON responses
    if len(full_text) > max_text_chars:
        full_text = full_text[:max_text_chars]

    return {
        "url": url,
        "title": final_title,
        "text": full_text,
        "images": images_list,
        "logos": logos_list,
        "colors": colors_list,
        "crawled_pages": crawled_count
    }
