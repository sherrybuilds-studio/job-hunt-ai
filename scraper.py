import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/de/search"
QUERIES = [
    "AI Developer",
    "AI Automation Engineer",
    "AI Consultant",
]


def _creds() -> tuple[str, str]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise ValueError("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set in environment")
    return app_id, app_key


async def _fetch_page(client: httpx.AsyncClient, query: str, page: int) -> list[dict]:
    app_id, app_key = _creds()
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "where": "Berlin",
        "distance": 25,
        "results_per_page": 20,
        "content-type": "application/json",
        "sort_by": "date",
    }
    response = await client.get(f"{ADZUNA_BASE}/{page}", params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


def _normalise(raw: dict) -> dict:
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    if salary_min and salary_max:
        salary = f"€{int(salary_min):,}–€{int(salary_max):,}"
    elif salary_min:
        salary = f"from €{int(salary_min):,}"
    else:
        salary = ""

    return {
        "title": raw.get("title", "").strip(),
        "company": raw.get("company", {}).get("display_name", "").strip(),
        "salary": salary,
        "description": raw.get("description", "").strip()[:800],
        "url": raw.get("redirect_url", "").strip(),
    }


async def scrape_jobs(pages_per_query: int = 2) -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient() as client:
        for query in QUERIES:
            for page in range(1, pages_per_query + 1):
                try:
                    results = await _fetch_page(client, query, page)
                    jobs = [_normalise(r) for r in results if r.get("redirect_url")]
                    new = [j for j in jobs if j["url"] not in seen_urls]
                    seen_urls.update(j["url"] for j in new)
                    all_jobs.extend(new)
                    logger.info(f"[{query}] page {page}: +{len(new)} jobs")
                    if len(results) < 20:
                        break  # no more pages
                    await asyncio.sleep(0.5)
                except httpx.HTTPStatusError as e:
                    logger.error(f"Adzuna HTTP {e.response.status_code} for '{query}' page {page}")
                except Exception as e:
                    logger.error(f"Adzuna error for '{query}' page {page}: {e}")

    logger.info(f"Total unique jobs scraped: {len(all_jobs)}")
    return all_jobs
