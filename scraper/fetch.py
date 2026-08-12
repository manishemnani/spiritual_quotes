"""Daily quote fetch — run hourly 06:00-23:00 IST by GitHub Actions.

Exit codes:
  0 - nothing to do (today's quote already stored, or not published yet)
      or new quotes stored successfully
  1 - the page fetched but yielded no parseable quotes (site changed - alert)
      or the fetch itself failed
"""

import sys

import quotes_lib as lib


def main() -> int:
    today = lib.today_ist().isoformat()
    store = lib.load_store()

    if today in store:
        print(f"Quote for {today} already stored - nothing to do.")
        return 0

    html = lib.fetch_page(1)
    quotes = lib.parse_quotes(html)
    if not quotes:
        print("ERROR: page fetched but no quotes parsed - "
              "site structure may have changed.", file=sys.stderr)
        return 1

    # Upsert everything on page 1 (~15 quotes): this also self-heals gaps
    # and picks up corrections to recent quotes.
    changed = lib.upsert(store, quotes)
    if changed:
        lib.write_outputs(store)
        print(f"Stored {changed} new/updated quote(s).")

    if today in store:
        print(f"Quote of the day ({today}) is in.")
    else:
        print(f"Quote for {today} not published yet - will retry next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
