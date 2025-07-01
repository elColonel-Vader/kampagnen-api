
from fastapi import FastAPI, Query
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List

app = FastAPI()

class AnalyzeResponse(BaseModel):
    url: str
    title: str
    text: str
    images: List[str]

def extract_with_playwright(target_url: str):
    images = []
    title = ""
    text = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(target_url, timeout=30000)
        html = page.content()
        browser.close()

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else ""
        text = soup.get_text()
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(urljoin(target_url, src))

    return title, text, images

@app.get("/crawl-analyze", response_model=AnalyzeResponse)
def crawl_analyze(url: str = Query(...)):
    title, text, images = extract_with_playwright(url)
    return {
        "url": url,
        "title": title,
        "text": text,
        "images": list(set(images))
    }
