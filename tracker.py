import os
import logging
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)
TABLE = "applications"


def _client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(url, key)


def already_tracked(url: str) -> bool:
    result = _client().table(TABLE).select("id").eq("url", url).execute()
    return len(result.data) > 0


def insert_job(job: dict, score: int, cover_letter: str) -> dict:
    row = {
        "job_title": job["title"],
        "company": job.get("company", ""),
        "url": job["url"],
        "score": score,
        "cover_letter": cover_letter,
        "status": "pending",
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    result = _client().table(TABLE).insert(row).execute()
    logger.info(f"Inserted: {job['title']} @ {job.get('company', '?')} (score {score})")
    return result.data[0] if result.data else {}


def mark_applied(url: str):
    _client().table(TABLE).update({"status": "applied"}).eq("url", url).execute()
    logger.info(f"Marked applied: {url}")


def get_pending() -> list[dict]:
    result = _client().table(TABLE).select("*").eq("status", "pending").execute()
    return result.data
