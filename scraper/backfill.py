"""One-time historical backfill - walks every listing page and stores all quotes.

Usage: python scraper/backfill.py [max_pages]
Polite: 1.5s delay between page fetches.
"""

import sys
import time

import quotes_lib as lib

DELAY_SECONDS = 1.5


def main() -> int:
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    store = lib.load_store()
    total_changed = 0

    page = 1
    while page <= max_pages:
        print(f"Fetching page {page}...")
        html = lib.fetch_page(page)
        quotes = lib.parse_quotes(html)
        if not quotes:
            print(f"No quotes parsed on page {page} - stopping.")
            break
        total_changed += lib.upsert(store, quotes)
        if f"?page={page + 1}" not in html:
            print("No next page link - reached the end.")
            break
        page += 1
        time.sleep(DELAY_SECONDS)

    if total_changed:
        lib.write_outputs(store)
    print(f"Done: {total_changed} new/updated quote(s), "
          f"{len(store)} total in store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
