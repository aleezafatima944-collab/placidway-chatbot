import json
import re
import time
from pathlib import Path

import requests
import trafilatura
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

# CHANGE THIS: put your real email
USER_AGENT = "PlacidWayAssessmentBot/1.0 (aleezafatima.944@gmail.com)"
DELAY_SECONDS = 1.0
RAW_DIR = Path("data/raw")
ROBOTS_URL = "https://www.placidway.com/robots.txt"

URLS = [
    "https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
    "https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
    "https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
    "https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
    "https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
    "https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
    "https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1",
]

HEADERS = {"User-Agent": USER_AGENT}


def load_robots():
    """Read robots.txt using our own User-Agent."""
    rp = RobotFileParser()
    try:
        resp = requests.get(ROBOTS_URL, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            rp.parse([])  # no robots rules found, allow
    except requests.RequestException as e:
        print(f"Could not read robots.txt ({e}). Continuing carefully.")
        rp.parse([])
    return rp


def extract_text(html):
    """Main text first (trafilatura). If too short, fall back to BeautifulSoup."""
    text = trafilatura.extract(
        html, include_tables=True, include_links=False, favor_recall=True
    )
    if text and len(text) > 200:
        return text.strip()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def extract_tables(html):
    """Read every table and turn each row into one line: | a | b | c |"""
    soup = BeautifulSoup(html, "html.parser")
    blocks = []
    for n, table in enumerate(soup.find_all("table"), start=1):
        heading = table.find_previous(["h1", "h2", "h3", "h4"])
        title = heading.get_text(" ", strip=True) if heading else f"Table {n}"
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append("| " + " | ".join(cells) + " |")
        if rows:
            blocks.append(title + "\n" + "\n".join(rows))
    return "\n\n".join(blocks)
def get_title(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.title.get_text(strip=True) if soup.title else ""


def scrape_all():
    """Scrape the 7 pages. Returns how many were saved."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rp = load_robots()
    saved = 0

    for i, url in enumerate(URLS, start=1):
        if not rp.can_fetch(USER_AGENT, url):
            print(f"[{i}] BLOCKED by robots.txt, skipped: {url}")
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            html = resp.text
            text = extract_text(html)
            if "search-medical-pricings" in url:
                tables = extract_tables(html)
                if tables:
                    text += "\n\nPRICE TABLES:\n" + tables
            record = {
                "url": url,
                "title": get_title(html),
                "text": text,
            }
           
            out = RAW_DIR / f"{i:02d}.json"
            out.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                           encoding="utf-8")
            print(f"[{i}] OK  {len(record['text']):>6} chars  {record['title'][:60]}")
            saved += 1
        except requests.RequestException as e:
            print(f"[{i}] ERROR {e}  ({url})")
        time.sleep(DELAY_SECONDS)  # 1 request per second

    print(f"\nDone. Saved {saved} of {len(URLS)} pages.")
    return saved


if __name__ == "__main__":
    scrape_all()