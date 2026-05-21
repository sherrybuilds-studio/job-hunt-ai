import asyncio
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

# ─── Firecrawl ────────────────────────────────────────────────────────────────

FIRECRAWL_SOURCES = [
    "https://berlinstartupjobs.com/skill-areas/working-student/",
    "https://berlinstartupjobs.com/skill-areas/ai/",
    # join.com requires login — dropping until a public URL is found
]

_JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "url": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title"],
            },
        }
    },
}

_EXTRACT_PROMPT = (
    "Extract every job listing from this page. "
    "For each job include: title, company name, "
    "direct URL to the job posting, and any description or requirements shown."
)


def _normalise_fc(raw: dict) -> dict:
    return {
        "title": raw.get("title", "").strip(),
        "company": raw.get("company", "").strip(),
        "salary": "",
        "description": raw.get("description", "").strip()[:800],
        "url": raw.get("url", "").strip(),
        "source": "firecrawl",
    }


def scrape_startup_boards() -> list[dict]:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.warning("FIRECRAWL_API_KEY not set — skipping startup boards")
        return []

    try:
        from firecrawl import V1FirecrawlApp, V1JsonConfig
    except ImportError:
        logger.warning("firecrawl-py not installed — skipping startup boards")
        return []

    fc = V1FirecrawlApp(api_key=api_key)
    all_jobs: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for url in FIRECRAWL_SOURCES:
        try:
            resp = fc.scrape_url(
                url,
                formats=["json", "markdown"],
                json_options=V1JsonConfig(
                    schema=_JOB_SCHEMA,
                    prompt=_EXTRACT_PROMPT,
                ),
                timeout=30000,
            )
            jobs_raw = (resp.json_field or {}).get("jobs", [])
            new = 0
            for raw in jobs_raw:
                title = raw.get("title", "").strip()
                company = raw.get("company", "").strip()
                if not title:
                    continue
                key = (company.lower(), title.lower())
                if key not in seen:
                    seen.add(key)
                    all_jobs.append(_normalise_fc(raw))
                    new += 1

            logger.info(f"[Firecrawl] {url}: +{new} jobs extracted")

            if new == 0:
                raw_preview = str(resp.json_field)[:500] if resp.json_field else "None"
                logger.warning(f"[Firecrawl] 0 jobs from {url}")
                logger.warning(f"[Firecrawl]   json_field = {raw_preview}")
                if resp.markdown:
                    logger.warning(f"[Firecrawl]   markdown preview = {resp.markdown[:400]}")
                else:
                    logger.warning(f"[Firecrawl]   no markdown returned (page may have blocked scraping)")

        except Exception as e:
            logger.error(f"Firecrawl error for {url}: {e}")

    logger.info(f"Firecrawl total unique jobs: {len(all_jobs)}")
    return all_jobs


# ─── Arbeitnow ────────────────────────────────────────────────────────────────

ARBEITNOW_ENDPOINTS = [
    "https://www.arbeitnow.com/api/job-board-api?q=werkstudent+AI&location=berlin",
    "https://www.arbeitnow.com/api/job-board-api?q=working+student+python&location=berlin",
]

_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text).strip()


def _normalise_arbeitnow(raw: dict) -> dict:
    tags = raw.get("tags", [])
    description = _strip_html(raw.get("description", ""))
    if tags:
        description = f"Tags: {', '.join(tags)}\n\n{description}"
    return {
        "title": raw.get("title", "").strip(),
        "company": raw.get("company_name", "").strip(),
        "salary": "",
        "description": description[:800],
        "url": raw.get("url", "").strip(),
        "source": "arbeitnow",
    }


async def scrape_arbeitnow() -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient() as client:
        for endpoint in ARBEITNOW_ENDPOINTS:
            try:
                response = await client.get(
                    endpoint,
                    timeout=20,
                    follow_redirects=True,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                # API returns {"data": [...]} or a bare list
                jobs_raw = data.get("data", data) if isinstance(data, dict) else data
                new = 0
                for raw in jobs_raw:
                    job_url = raw.get("url", "").strip()
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)
                    all_jobs.append(_normalise_arbeitnow(raw))
                    new += 1
                logger.info(f"[Arbeitnow] {endpoint}: +{new} jobs")
            except httpx.HTTPStatusError as e:
                logger.error(f"Arbeitnow HTTP {e.response.status_code} for {endpoint}")
            except Exception as e:
                logger.error(f"Arbeitnow error for {endpoint}: {e}")

    logger.info(f"Arbeitnow total unique jobs: {len(all_jobs)}")
    return all_jobs


# ─── Adzuna ───────────────────────────────────────────────────────────────────

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/de/search"

# Primary: werkstudent-specific terms that match the must-have filter directly
QUERIES_PRIMARY = [
    "Werkstudent AI",
    "Werkstudent Python",
    "Working Student AI",
    "Working Student Python",
    "Working Student LLM",
    "Werkstudent Automation",
]

# Fallback: broader AI dev search — 1 page only, must-have filter weeds seniors
QUERIES_FALLBACK = [
    "AI Developer Berlin",
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
        "source": "adzuna",
    }


async def scrape_jobs(pages_per_query: int = 2) -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient() as client:
        # Primary werkstudent queries — full pages_per_query depth
        for query in QUERIES_PRIMARY:
            for page in range(1, pages_per_query + 1):
                try:
                    results = await _fetch_page(client, query, page)
                    jobs = [_normalise(r) for r in results if r.get("redirect_url")]
                    new = [j for j in jobs if j["url"] not in seen_urls]
                    seen_urls.update(j["url"] for j in new)
                    all_jobs.extend(new)
                    logger.info(f"[Adzuna primary] '{query}' page {page}: +{len(new)} jobs")
                    if len(results) < 20:
                        break
                    await asyncio.sleep(0.5)
                except httpx.HTTPStatusError as e:
                    logger.error(f"Adzuna HTTP {e.response.status_code} for '{query}' page {page}")
                except Exception as e:
                    logger.error(f"Adzuna error for '{query}' page {page}: {e}")

        # Fallback broad query — 1 page only
        for query in QUERIES_FALLBACK:
            try:
                results = await _fetch_page(client, query, 1)
                jobs = [_normalise(r) for r in results if r.get("redirect_url")]
                new = [j for j in jobs if j["url"] not in seen_urls]
                seen_urls.update(j["url"] for j in new)
                all_jobs.extend(new)
                logger.info(f"[Adzuna fallback] '{query}' page 1: +{len(new)} jobs")
            except httpx.HTTPStatusError as e:
                logger.error(f"Adzuna HTTP {e.response.status_code} for fallback '{query}'")
            except Exception as e:
                logger.error(f"Adzuna error for fallback '{query}': {e}")

    logger.info(f"Adzuna total unique jobs: {len(all_jobs)}")
    return all_jobs
