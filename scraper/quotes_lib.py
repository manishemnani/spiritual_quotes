"""Shared library for fetching, parsing and storing Sri M quotes.

Storage layout (repo root):
  quotes/<year>.json  - all quotes for a year, ascending by date
  latest.json         - newest 30 quotes, descending (the file the app polls)
  manifest.json       - latest_date / total_count / years

A quote's id IS its date (YYYY-MM-DD): the site publishes one quote per day,
and this makes client-side delta sync a single date comparison.
"""

import html
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://satsang-foundation.org/sri-m/quotes"
SITE_ROOT = "https://satsang-foundation.org"
# The site 403s generic client UAs (curl, python-requests) but accepts an
# honest identifying one — verified 2026-08-11.
USER_AGENT = "Mozilla/5.0 (compatible; SatsangQuotesFetcher/1.0)"
IST = ZoneInfo("Asia/Kolkata")
AUTHOR = "Sri M"
LATEST_COUNT = 30
MIN_TEXT_LEN = 10
MAX_TEXT_LEN = 5000
# Long quotes are truncated on listing pages with a trailing ellipsis and a
# "Read more" link to a /posts-and-updates/... detail page holding full text.
TRUNCATION_MARKERS = ("...", "…")
DETAIL_FETCH_DELAY = 1.0

REPO_ROOT = Path(__file__).resolve().parent.parent
QUOTES_DIR = REPO_ROOT / "quotes"
LATEST_FILE = REPO_ROOT / "latest.json"
MANIFEST_FILE = REPO_ROOT / "manifest.json"

DATE_RE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4})")

# Promotional boilerplate appended to many 2022-2023 posts; usually inside a
# .wp-block-group container, but scrub by text too in case it isn't.
PROMO_RES = (
    re.compile(r"Sri M[’']s Quotes are now available in regional languages.*$",
               re.I | re.S),
    re.compile(r"To receive them every morning,? please Follow\s*&\s*Subscribe.*$",
               re.I | re.S),
)


def today_ist() -> date:
    return datetime.now(IST).date()


def fetch_page(page: int = 1) -> str:
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def _clean_text(raw: str) -> str:
    # The site double-encodes some entities (&amp;nbsp;), so one decode by the
    # HTML parser can still leave literal &nbsp;/&amp; in the text.
    text = html.unescape(raw).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    # Inline markup (<em>maya</em>) leaves stray spaces before punctuation.
    text = re.sub(r"\s+([.,;:!?])", r"\1", text).strip()
    return text.strip("“”\"' ").strip()


def prefix_match(a: str, b: str, n: int = 20) -> bool:
    """Whitespace-insensitive comparison of two texts' openings — inline
    markup on detail pages shifts spacing (e.g. 'T he mind' vs 'The mind')."""
    squash = lambda s: re.sub(r"\s+", "", s)[:n]
    return squash(a) == squash(b)


def strip_promo(text: str) -> str:
    for pattern in PROMO_RES:
        text = pattern.sub("", text)
    return text.strip()


def fetch_full_text(detail_href: str) -> str | None:
    """Fetch a quote's full text from its 'Read more' detail page.

    Templates vary by era: newer posts hold the text in <p> tags inside
    div.journal-article, 2015-era posts as bare text nodes in that div, and
    2022-2023 posts append a promo block. Removing non-content elements and
    taking the div's remaining text handles all of them.
    """
    url = SITE_ROOT + detail_href if detail_href.startswith("/") else detail_href
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    time.sleep(DETAIL_FETCH_DELAY)
    soup = BeautifulSoup(resp.text, "html.parser")
    body = soup.select_one("div.journal-article")
    if body is None:
        return None
    for el in body.select(".wp-block-group, figure, figcaption, ul, "
                          "h1, h2, h3, h4, h5, h6"):
        el.decompose()
    text = strip_promo(_clean_text(body.get_text(" ", strip=True)))
    return text or None


def parse_quotes(html: str, resolve_read_more: bool = True) -> list[dict]:
    """Parse every quote on one listing page (featured + list articles).

    When resolve_read_more is set, quotes truncated on the listing (trailing
    ellipsis + a "Read more" link) are completed from their detail page.
    """
    soup = BeautifulSoup(html, "html.parser")
    quotes = []
    for article in soup.find_all("article"):
        blockquote = article.find("blockquote")
        if blockquote is None:
            continue
        text = _clean_text(blockquote.get_text(" ", strip=True))
        # The metadata date sits after the blockquote, so the last date-shaped
        # string in the article text is the publication date.
        meta_text = article.get_text(" ", strip=True)
        dates = DATE_RE.findall(meta_text)
        if not dates:
            continue
        try:
            published = datetime.strptime(dates[-1], "%B %d, %Y").date()
        except ValueError:
            continue

        source_url = BASE_URL
        read_more = article.find("a", string=re.compile(r"read more", re.I))
        if read_more and read_more.get("href"):
            source_url = SITE_ROOT + read_more["href"]
            if resolve_read_more and text.endswith(TRUNCATION_MARKERS):
                full = fetch_full_text(read_more["href"])
                # Sanity check: the full text must begin like the listing
                # snippet, otherwise we grabbed the wrong content.
                if full and prefix_match(full, text):
                    text = full
                else:
                    print(f"WARNING: could not resolve full text for "
                          f"{published}, keeping truncated.", file=sys.stderr)

        if not (MIN_TEXT_LEN <= len(text) <= MAX_TEXT_LEN):
            print(f"WARNING: skipping implausible quote for {published}: "
                  f"{len(text)} chars", file=sys.stderr)
            continue
        quotes.append({
            "id": published.isoformat(),
            "date": published.isoformat(),
            "text": text,
            "author": AUTHOR,
            "source_url": source_url,
        })
    return quotes


def load_store() -> dict[str, dict]:
    """Load all year files into one {date: quote} dict."""
    store = {}
    if QUOTES_DIR.is_dir():
        for path in sorted(QUOTES_DIR.glob("*.json")):
            for quote in json.loads(path.read_text(encoding="utf-8")):
                store[quote["date"]] = quote
    return store


def upsert(store: dict[str, dict], quotes: list[dict]) -> int:
    """Insert new quotes / overwrite corrected ones. Returns change count."""
    changed = 0
    for quote in quotes:
        existing = store.get(quote["date"])
        if existing != quote:
            action = "updated" if existing else "added"
            print(f"{action}: {quote['date']}")
            store[quote["date"]] = quote
            changed += 1
    return changed


def write_outputs(store: dict[str, dict]) -> None:
    """Rewrite year files, latest.json and manifest.json from the store."""
    ordered = sorted(store.values(), key=lambda q: q["date"])

    QUOTES_DIR.mkdir(exist_ok=True)
    years = sorted({q["date"][:4] for q in ordered})
    for year in years:
        year_quotes = [q for q in ordered if q["date"].startswith(year)]
        _dump(QUOTES_DIR / f"{year}.json", year_quotes)

    _dump(LATEST_FILE, list(reversed(ordered[-LATEST_COUNT:])))
    _dump(MANIFEST_FILE, {
        "latest_date": ordered[-1]["date"] if ordered else None,
        "total_count": len(ordered),
        "years": [int(y) for y in years],
    })


def _dump(path: Path, data) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
