from fastapi import FastAPI, Query
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set

app = FastAPI()

class AnalyzeResponse(BaseModel):
    url: str
    title: str
    text: str
    images: List[str]

# Hilfsfunktion zur Prüfung auf gleiche Domain
def is_same_domain(base: str, target: str) -> bool:
    return urlparse(base).netloc == urlparse(target).netloc

@app.get("/crawl-analyze", response_model=AnalyzeResponse)
def crawl_analyze(url: str = Query(...)):
    visited: Set[str] = set()
    to_visit: List[str] = [url]
    all_images: Set[str] = set()
    full_text = ""
    final_title = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()

        while to_visit and len(visited) < 5:
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

                # Bildquellen aus <img>, <meta>, <link>, <source>
                for tag in soup.find_all(["img", "meta", "link", "source"]):
                    src = tag.get("src") or tag.get("content") or tag.get("href") or tag.get("srcset")
                    if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".svg"]):
                        all_images.add(urljoin(current_url, src))

                # Interne Links sammeln
                for link in soup.find_all("a", href=True):
                    href = urljoin(current_url, link["href"])
                    if is_same_domain(url, href) and href not in visited and href not in to_visit:
                        to_visit.append(href)

                visited.add(current_url)
            except Exception as e:
                print(f"Fehler bei {current_url}: {e}")
                continue

        browser.close()

    # Mindestens 10 Bilder sicherstellen
    while len(all_images) < 10:
        all_images.add("https://via.placeholder.com/600x400?text=Platzhalter")

    return {
        "url": url,
        "title": final_title,
        "text": full_text.strip(),
        "images": list(all_images)
    }
