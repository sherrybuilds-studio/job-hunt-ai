# CV Job Hunter

Automated daily pipeline that scrapes Indeed.de for AI jobs in Berlin, scores them with Claude, writes cover letters, saves to Supabase, and sends a Telegram digest at 08:00.

## File map

| File | Purpose |
|---|---|
| `profile.py` | Single source of truth — `MY_PROFILE` dataclass, import from here |
| `cv_builder.py` | Generates `sherry_cv.pdf` from profile using reportlab |
| `scraper.py` | Async Indeed.de scraper (httpx + BeautifulSoup) |
| `matcher.py` | Claude scores each job 1–100 with prompt caching on profile block |
| `writer.py` | Claude writes a tailored cover letter per job (≤300 words) |
| `tracker.py` | Supabase client — insert/dedup/mark-applied for `applications` table |
| `notifier.py` | Sends Telegram digest of top 3 jobs |
| `agent.py` | Orchestrator — runs the full pipeline, supports `--dry-run` |
| `setup.sql` | Supabase table schema (run once) |

## Profile

- **Name:** Muhammad Shehryar (Sherry)
- **Email:** sherrybuilds@gmail.com
- **Location:** Berlin, Germany
- **GitHub:** sherrybuilds-studio
- **Skills:** Python, FastAPI, ChromaDB, n8n, RAG, Semantic Caching, WhatsApp Bots, VPS/PM2, Supabase, Anthropic SDK, OpenRouter
- **Target roles:** AI Developer, AI Automation Engineer, AI Consultant
- **Target salary:** €55,000–€75,000

## Stack

- Anthropic SDK (`claude-sonnet-4-6`) for matching and cover letter writing
- Supabase for application tracking
- python-telegram-bot for notifications
- httpx + BeautifulSoup for scraping
- reportlab for PDF CV generation

## Environment variables

Copy `.env.example` to `.env` and fill in all seven keys:
```
ANTHROPIC_API_KEY
SUPABASE_URL
SUPABASE_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
ADZUNA_APP_ID       # free at developer.adzuna.com
ADZUNA_APP_KEY
```

## Setup

```bash
pip install -r requirements.txt
# Run setup.sql in Supabase SQL editor once
python agent.py --dry-run   # test without writes
python agent.py             # live run
python cv_builder.py        # regenerate PDF CV
```

## Scheduling (PM2 on VPS)

```js
// ecosystem.config.js
{ script: "agent.py", cron_restart: "0 8 * * *", interpreter: "python3" }
```

## Coding rules

- All keys via `os.getenv()` — never hardcoded
- f-strings, small focused functions
- English-only comments
- `--dry-run` flag skips all writes and Telegram
