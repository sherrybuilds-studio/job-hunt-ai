# CV Job Hunter

Automated daily pipeline that scrapes Berlin AI job boards, scores matches with rule-based weighted scoring, writes cover letters with Claude, saves to Supabase, and sends a Telegram digest at 08:00.

## File map

| File | Purpose |
|---|---|
| `profile.py` | Single source of truth — `PROFILE` dict + `MY_PROFILE` compat shim, import from here |
| `cv_builder.py` | Generates `sherry_cv.pdf` from profile using reportlab |
| `scraper.py` | Multi-source scraper: Adzuna API, Arbeitnow API, Firecrawl (berlinstartupjobs) |
| `matcher.py` | Rule-based weighted scoring (max 105 pts) — no LLM calls, instant, free |
| `writer.py` | Claude writes a tailored cover letter per job (≤300 words) via OpenRouter |
| `tracker.py` | Supabase client — insert/dedup/mark-applied for `applications` table |
| `notifier.py` | Sends Telegram digest: 🔥 MATCHES above threshold + 📊 TOP 5 TODAY |
| `agent.py` | Orchestrator — merges 3 sources, scores all, saves JSON, supports `--dry-run` |
| `setup.sql` | Supabase table schema (run once) |
| `data/top_matches.json` | Per-run history: date, scraped count, matched count, top 10 scored jobs |

## Profile

- **Name:** Muhammad Shehryar (Sherry)
- **Email:** shehryarmughal30@gmail.com
- **Location:** Berlin, Germany
- **GitHub:** sherrybuilds-studio
- **Skills:** Python, FastAPI, ChromaDB, n8n, RAG, Semantic Caching, WhatsApp Bots, VPS/PM2, Supabase, Langfuse, Docker
- **Target roles:** Werkstudent AI, Working Student AI/LLM/Automation, AI Engineering Intern
- **Availability:** 20 hrs/week | Student visa with Werkstudent permission

## Stack

- OpenRouter (`anthropic/claude-3.5-haiku`) for cover letter writing
- Rule-based keyword scoring for job matching (no LLM cost)
- Supabase for application tracking
- python-telegram-bot for notifications
- httpx for async HTTP (Adzuna, Arbeitnow)
- firecrawl-py for berlinstartupjobs scraping
- reportlab for PDF CV generation

## Environment variables

Copy `.env.example` to `.env` and fill in all keys:
```
OPENROUTER_API_KEY
SUPABASE_URL
SUPABASE_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
ADZUNA_APP_ID       # free at developer.adzuna.com
ADZUNA_APP_KEY
FIRECRAWL_API_KEY   # free tier at firecrawl.dev
```

## Setup

```bash
pip install -r requirements.txt
# Run setup.sql in Supabase SQL editor once
python agent.py --dry-run             # test without writes
python agent.py                       # live run
python agent.py --min-score 25        # lower threshold to see more jobs
python cv_builder.py                  # regenerate PDF CV
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
