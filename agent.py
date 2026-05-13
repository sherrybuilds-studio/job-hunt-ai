import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from matcher import match_jobs
from notifier import send_digest
from scraper import scrape_jobs
from tracker import already_tracked, insert_job
from writer import write_cover_letter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agent")


async def run(dry_run: bool = False, min_score: int = 60, pages: int = 2):
    logger.info(f"Starting cv-job-hunter | dry_run={dry_run} min_score={min_score}")

    # 1 — scrape
    raw_jobs = await scrape_jobs(pages_per_query=pages)
    logger.info(f"Scraped {len(raw_jobs)} total unique jobs")

    # 2 — deduplicate against Supabase
    if dry_run:
        new_jobs = raw_jobs
        logger.info("[DRY RUN] Skipping Supabase dedup — treating all as new")
    else:
        new_jobs = [j for j in raw_jobs if not already_tracked(j["url"])]
        logger.info(f"{len(new_jobs)} new jobs (not yet in Supabase)")

    if not new_jobs:
        logger.info("No new jobs to process")
        if not dry_run:
            await send_digest([])
        return

    # 3 — score with Claude
    matched = match_jobs(new_jobs, min_score=min_score)
    logger.info(f"{len(matched)} jobs scored ≥{min_score}")

    if not matched:
        logger.info("No jobs passed the score threshold")
        if not dry_run:
            await send_digest([])
        return

    # 4 — cover letters + save
    for job in matched:
        title = f"{job['title']} @ {job.get('company', '?')}"
        logger.info(f"Writing cover letter for: {title} (score {job['score']})")
        cover_letter = write_cover_letter(job)
        if cover_letter is None:
            continue

        if dry_run:
            preview = cover_letter[:200].replace("\n", " ")
            logger.info(f"[DRY RUN] Letter preview: {preview}...")
        else:
            insert_job(job, score=job["score"], cover_letter=cover_letter)

    # 5 — Telegram digest
    if dry_run:
        logger.info("[DRY RUN] Telegram send skipped")
        logger.info(f"Top match: {matched[0]['title']} — {matched[0]['score']}/100")
    else:
        await send_digest(matched)

    logger.info("Run complete")


def main():
    parser = argparse.ArgumentParser(description="CV Job Hunter — daily AI job pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip Supabase writes and Telegram")
    parser.add_argument("--min-score", type=int, default=60, help="Minimum Claude score to keep a job (default 60)")
    parser.add_argument("--pages", type=int, default=2, help="Indeed pages to scrape per query (default 2)")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, min_score=args.min_score, pages=args.pages))


if __name__ == "__main__":
    main()
