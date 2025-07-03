from fastapi import FastAPI, Query
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict

app = FastAPI()

class AnalyzeResponse(BaseModel):
    url: str
    title: str
    text: str
    images: List[str]
    crawled_pages: int

# Hilfsfunktion zur Prüfung auf gleiche Domain
def is_same_domain(base: str, target: str) -> bool:
    return urlparse(base).netloc == urlparse(target).netloc

@app.get("/crawl-analyze", response_model=AnalyzeResponse)
def crawl_analyze(
    url: str = Query(...),
    max_pages: int = Query(5, description="Maximale Anzahl an Seiten"),
    min_images: int = Query(10, description="Minimale Anzahl an Bildern")
):
    visited: Set[str] = set()
    to_visit: List[str] = [url]
    all_images: Set[str] = set()
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
                        all_images.add(urljoin(current_url, src))

                for link in soup.find_all("a", href=True):
                    href = urljoin(current_url, link["href"])
                    if is_same_domain(url, href) and href not in visited and href not in to_visit:
                        to_visit.append(href)

                visited.add(current_url)
                crawled_count += 1
            except Exception as e:
                print(f"Fehler bei {current_url}: {e}")
                continue

        browser.close()

    if len(all_images) < min_images:
        missing = min_images - len(all_images)
        for i in range(missing):
            all_images.add(
                f"https://via.placeholder.com/600x400?text=Platzhalter{i+1}"
            )

    return {
        "url": url,
        "title": final_title,
        "text": full_text.strip(),
        "images": list(all_images),
        "crawled_pages": crawled_count
    }
