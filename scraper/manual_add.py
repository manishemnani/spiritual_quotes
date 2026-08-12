"""Manual escape hatch - add or correct one quote by hand.

Used by the add-quote workflow (workflow_dispatch) if the site ever blocks
the scraper or publishes a quote the parser cannot read.

Usage: python scraper/manual_add.py YYYY-MM-DD "Quote text..."
"""

import sys
from datetime import date

import quotes_lib as lib


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1

    quote_date = date.fromisoformat(sys.argv[1]).isoformat()
    text = sys.argv[2].strip()
    if not (lib.MIN_TEXT_LEN <= len(text) <= lib.MAX_TEXT_LEN):
        print(f"ERROR: text length {len(text)} outside "
              f"{lib.MIN_TEXT_LEN}-{lib.MAX_TEXT_LEN}.", file=sys.stderr)
        return 1

    store = lib.load_store()
    changed = lib.upsert(store, [{
        "id": quote_date,
        "date": quote_date,
        "text": text,
        "author": lib.AUTHOR,
        "source_url": lib.BASE_URL,
    }])
    if changed:
        lib.write_outputs(store)
        print(f"Stored quote for {quote_date}.")
    else:
        print(f"Quote for {quote_date} already identical - no change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
