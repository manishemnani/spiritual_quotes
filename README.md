# Daily quotes — data & scraper

Zero-cost backend for a daily-quotes mobile app. A GitHub Actions cron
scrapes the day's quote from the source website and commits it to this
repo — **the repo is the database**, served free over
`raw.githubusercontent.com`.

## Layout

| Path | Contents |
| --- | --- |
| `quotes/<year>.json` | All quotes for a year, ascending by date |
| `latest.json` | Newest 30 quotes, descending — the file the app polls daily |
| `manifest.json` | `latest_date`, `total_count`, `years` |
| `scraper/` | Fetch, backfill and manual-add scripts (Python) |
| `.github/workflows/` | Cron fetch, manual add, monthly keep-alive |

A quote's `id` is its date (`YYYY-MM-DD`) — the source publishes one quote
per day, which makes client delta-sync a single date comparison.

## How ingestion works

- `fetch-quote.yml` runs hourly **06:00–23:00 IST**. `fetch.py` exits
  immediately if today's quote is already stored (idempotent guard); otherwise
  it scrapes the listing page, validates, and upserts everything found — which
  also self-heals gaps and picks up corrections to the last ~15 days.
- Quotes truncated on the listing ("Read more") are completed from their
  detail pages.
- The workflow commits only when files actually changed.
- If parsing yields zero quotes the run **fails loudly** — GitHub emails the
  failure, which is the alerting.
- `add-quote.yml` (`workflow_dispatch`) is the manual escape hatch: paste a
  date and text if the parser is ever broken.
- `keepalive.yml` commits monthly so GitHub never disables the cron after 60
  quiet days.

## Local usage

```bash
pip install -r scraper/requirements.txt
python scraper/backfill.py     # one-time full history crawl (polite delays)
python scraper/fetch.py        # what the cron runs
```

Run the scripts from the `scraper/` directory or with it on `PYTHONPATH`.

## Notes

- The source site rejects generic client user-agents; the scraper identifies
  itself honestly, which the site accepts.
- Quote content is © its original publisher. This project republishes it for
  a companion app — obtain the publisher's written permission before public
  release.
