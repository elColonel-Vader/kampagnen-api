
# Kampagnen API mit Playwright

Diese FastAPI-Anwendung crawlt Websites mit einem Headless-Browser (Playwright) und extrahiert Titel, Text & Bilder.

## Installation

```bash
pip install -r requirements.txt
playwright install
```

## API

Der Endpunkt `/crawl-analyze` akzeptiert folgende Query-Parameter:

- `url` (erforderlich): Startadresse der zu crawlenden Website
- `max_pages` (optional, Standard `5`): Maximale Anzahl von Seiten
- `min_images` (optional, Standard `10`): Minimale Anzahl an Bildern im Ergebnis
- `page_timeout` (optional, Standard `30000`): Zeitlimit in Millisekunden pro Seite

Mit `page_timeout` kann das Timeout bei langsamen Seiten erhöht werden.

## Deploy mit 1 Klick auf Render.com

1. Forke dieses Repository auf GitHub
2. Gehe zu https://render.com/import
3. Wähle dein GitHub-Repo und deploye
