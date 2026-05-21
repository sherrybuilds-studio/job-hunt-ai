import argparse
import asyncio
import json
import logging
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from matcher import match_jobs
from notifier import send_digest
from scraper import scrape_arbeitnow, scrape_jobs, scrape_startup_boards
from tracker import already_tracked, insert_job
from writer import write_cover_letter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agent")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_JSON_PATH = os.path.join(_DATA_DIR, "top_matches.json")


def _merge(lists: list[list[dict]]) -> list[dict]:
    seen_urls: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    merged: list[dict] = []
    for jobs in lists:
        for job in jobs:
            url = job.get("url", "").strip()
            key = (job.get("company", "").lower(), job.get("title", "").lower())
            if url and url in seen_urls:
                continue
            if key in seen_keys:
                continue
            if url:
                seen_urls.add(url)
            seen_keys.add(key)
            merged.append(job)
    return merged


def _save_run_data(
    run_date: str,
    total_scraped: int,
    matched_count: int,
    all_scored: list[dict],
):
    os.makedirs(_DATA_DIR, exist_ok=True)
    existing: list[dict] = []
    if os.path.exists(_JSON_PATH):
        try:
            with open(_JSON_PATH) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

    entry = {
        "date": run_date,
        "total_scraped": total_scraped,
        "matched_count": matched_count,
        "top_10": [
            {
                "title": j["title"],
                "company": j.get("company", ""),
                "score": j["score"],
                "matched_skills": j.get("matched_skills", []),
                "url": j.get("url", ""),
                "source": j.get("source", ""),
            }
            for j in all_scored[:10]
        ],
    }
    existing.append(entry)
    with open(_JSON_PATH, "w") as f:
        json.dump(existing, f, indent=2)
    logger.info(f"Run data saved to {_JSON_PATH}")


async def run(dry_run: bool = False, min_score: int = 40, pages: int = 2):
    run_date = date.today().isoformat()
    logger.info(f"Starting cv-job-hunter | dry_run={dry_run} min_score={min_score} date={run_date}")

    # 1 — scrape all sources
    adzuna_jobs = await scrape_jobs(pages_per_query=pages)
    arbeitnow_jobs = await scrape_arbeitnow()
    fc_jobs = scrape_startup_boards()

    raw_jobs = _merge([adzuna_jobs, arbeitnow_jobs, fc_jobs])
    total_scraped = len(raw_jobs)
    logger.info(
        f"Total unique jobs after merge: {total_scraped} "
        f"(adzuna={len(adzuna_jobs)}, arbeitnow={len(arbeitnow_jobs)}, firecrawl={len(fc_jobs)})"
    )

    # 2 — deduplicate against Supabase
    if dry_run:
        new_jobs = raw_jobs
        logger.info("[DRY RUN] Skipping Supabase dedup — treating all as new")
    else:
        new_jobs = [j for j in raw_jobs if not already_tracked(j["url"])]
        logger.info(f"{len(new_jobs)} new jobs (not yet in Supabase)")

    # 3 — score ALL jobs (min_score=0 to keep every job for top5)
    all_scored = match_jobs(new_jobs, min_score=0)
    matched = [j for j in all_scored if j["score"] >= min_score]
    top5 = all_scored[:5]

    logger.info(f"Scored {len(all_scored)} jobs — {len(matched)} ≥ {min_score}, top5 max score: {top5[0]['score'] if top5 else 0}")

    # 4 — save run data (always, including dry-run)
    _save_run_data(run_date, total_scraped, len(matched), all_scored)

    if not new_jobs:
        logger.info("No new jobs to process")
        if not dry_run:
            await send_digest([], top5=top5, total_scraped=total_scraped, min_score=min_score)
        return

    # 5 — cover letters for matched jobs only
    for job in matched:
        title = f"{job['title']} @ {job.get('company', '?')}"
        logger.info(f"Writing cover letter: {title} (score {job['score']})")
        cover_letter = write_cover_letter(job)
        if cover_letter is None:
            continue

        if dry_run:
            preview = cover_letter[:200].replace("\n", " ")
            logger.info(f"[DRY RUN] Letter preview: {preview}...")
        else:
            insert_job(job, score=job["score"], cover_letter=cover_letter)

    # 6 — Telegram digest
    if dry_run:
        logger.info("[DRY RUN] Telegram send skipped")
        if top5:
            logger.info(f"Top match: {top5[0]['title']} @ {top5[0].get('company','?')} — {top5[0]['score']}/105")
    else:
        await send_digest(matched, top5=top5, total_scraped=total_scraped, min_score=min_score)

    logger.info("Run complete")


def main():
    parser = argparse.ArgumentParser(description="CV Job Hunter — daily AI job pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip Supabase writes and Telegram")
    parser.add_argument("--min-score", type=int, default=40, help="Minimum score to keep a job (default 40)")
    parser.add_argument("--pages", type=int, default=2, help="Adzuna pages per query (default 2)")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, min_score=args.min_score, pages=args.pages))


if __name__ == "__main__":
    main()
