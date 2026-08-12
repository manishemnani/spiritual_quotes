# Sri M Daily Quotes — data & scraper

Zero-cost backend for the Sri M quotes Android app. A GitHub Actions cron
scrapes the daily quote from
[satsang-foundation.org/sri-m/quotes](https://satsang-foundation.org/sri-m/quotes)
and commits it to this repo — **the repo is the database**, served free over
`raw.githubusercontent.com`.

## Layout

| Path | Contents |
| --- | --- |
| `quotes/<year>.json` | All quotes for a year, ascending by date |
| `latest.json` | Newest 30 quotes, descending — the file the app polls daily |
| `manifest.json` | `latest_date`, `total_count`, `years` |
| `scraper/` | Fetch, backfill and manual-add scripts (Python) |
| `.github/workflows/` | Cron fetch, manual add, monthly keep-alive |

A quote's `id` is its date (`YYYY-MM-DD`) — the site publishes one quote per
day, which makes client delta-sync a single date comparison.

## How ingestion works

- `fetch-quote.yml` runs hourly **06:00–23:00 IST**. `fetch.py` exits
  immediately if today's quote is already stored (idempotent guard); otherwise
  it scrapes page 1, validates (length 10–1500 chars, real date), and upserts
  everything found — which also self-heals gaps and picks up corrections to
  the last ~15 days.
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
python scraper/backfill.py     # one-time full history crawl (1.5s/page delay)
python scraper/fetch.py        # what the cron runs
```

Run the scripts from the `scraper/` directory or with it on `PYTHONPATH`.

## Notes

- The site 403s generic client user-agents; the scraper identifies itself as
  `Mozilla/5.0 (compatible; SatsangQuotesFetcher/1.0)`, which the site accepts.
- Quotes are © The Satsang Foundation. This project republishes them for a
  companion app — obtain the Foundation's written permission before public
  release.
