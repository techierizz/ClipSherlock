"""
Standalone Playwright crawler — runs as a separate subprocess to avoid
Streamlit's async event-loop conflict with sync_playwright.

Strategy:
  1. Use the Gemini API (via requests) to get a list of known piracy / 
     illegal sports streaming site URLs.
  2. Open ONE visible browser window.
  3. Load a YouTube search for sports piracy in Tab 1 (main tab).
  4. For each Gemini-suggested URL, open a NEW TAB (not a new window)
     in the same browser, visit the URL, scrape a snippet. Keep the tabs open 
     so the user can see them before the browser closes at the end.
  5. Output JSON to stdout for the parent Streamlit process.
"""

import json, sys, time, os, requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_piracy_urls_from_gemini():
    """Ask Gemini for a list of known piracy site URLs to investigate."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are a digital forensics analyst. List exactly 5 well-known, publicly documented "
        "illegal sports streaming or media piracy websites (sites that have been reported by news "
        "outlets, court cases, or anti-piracy organisations). "
        "Return ONLY a JSON array of objects, no markdown, no extra text. "
        'Format: [{"title": "Site Name", "url": "https://example.com", "risk": "HIGH"}]'
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        # Fallback list of publicly documented piracy sites (per RIAA/MPAA reports)
        return [
            {"title": "Stream2Watch (archived)", "url": "https://www.stream2watch.ws", "risk": "HIGH"},
            {"title": "Cricfree",                "url": "https://cricfree.sc",          "risk": "HIGH"},
            {"title": "FirstRowSports",           "url": "https://firstrowsports.eu",    "risk": "HIGH"},
            {"title": "SportRAR",                 "url": "https://sportrar.tv",          "risk": "CRITICAL"},
            {"title": "Buffstream",               "url": "https://buffstreams.app",      "risk": "HIGH"},
        ]


def run():
    from playwright.sync_api import sync_playwright

    # Step 1: Get URLs from Gemini
    piracy_sites = get_piracy_urls_from_gemini()

    scraped_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        # Tab 1 — YouTube search results page (stays open as reference)
        main_tab = context.new_page()
        main_tab.goto(
            "https://www.youtube.com/results?search_query=illegal+sports+streaming+piracy+sites",
            wait_until="domcontentloaded",
            timeout=20000
        )

        # Tabs 2-6 — one per piracy site, opened & closed in sequence
        for i, site in enumerate(piracy_sites[:5]):
            tab = context.new_page()
            snippet = "Could not retrieve page content."
            try:
                tab.goto(site["url"], wait_until="domcontentloaded", timeout=15000)
                tab.wait_for_timeout(2000)        # let user see the tab
                para = tab.query_selector("p")
                if para:
                    snippet = para.inner_text()[:300]
            except Exception:
                pass

            scraped_data.append({
                "id":      i + 1,
                "title":   site.get("title", site["url"]),
                "url":     site["url"],
                "risk":    site.get("risk", "UNKNOWN"),
                "snippet": snippet,
            })

            time.sleep(1.5)    # brief pause so user can see the tab

        time.sleep(3.0)  # brief pause at the end so user can see all open tabs before closing
        browser.close()

    print(json.dumps(scraped_data, ensure_ascii=False))


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(json.dumps([{"error": str(e)}]))
        sys.exit(1)
