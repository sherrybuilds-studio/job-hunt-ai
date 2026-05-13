import json
import logging
import os

from openai import OpenAI

from profile import MY_PROFILE

logger = logging.getLogger(__name__)

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
_PROFILE_TEXT = MY_PROFILE.as_text()
_MODEL = "anthropic/claude-3.5-haiku"

_SYSTEM = """You are a job-fit evaluator. Given a candidate profile and a job posting, return a JSON object with exactly these keys:
- score: integer 1-100 (how well this job fits the candidate's skills and targets)
- reasons: list of 2-3 short strings explaining the match
- red_flags: list of short strings for concerns (empty list if none)

Scoring guide:
- 80-100: strong match — werkstudent or junior/part-time AI role in Berlin, skills align
- 60-79: decent match, some relevant skills, worth applying
- below 60: poor fit, missing key requirements or wrong domain

Penalise heavily (score below 50) if:
- job is outside Berlin and not remote
- job requires full-time and does not mention werkstudent or part-time options
- job requires 3+ years experience or senior seniority

Return ONLY valid JSON with no markdown fences."""


_DEALBREAKERS = [
    "senior required", "5+ years", "management consulting",
    "vollzeit only", "full-time only", "c++ required",
]
_BONUS_KEYWORDS = ["werkstudent", "part-time", "teilzeit", "junior"]


_TITLE_DEALBREAKERS = ["senior"]


def _check_dealbreakers(job: dict) -> bool:
    title = job.get("title", "").lower()
    body = (title + " " + job.get("description", "")).lower()
    return any(kw in title for kw in _TITLE_DEALBREAKERS) or any(kw in body for kw in _DEALBREAKERS)


def _bonus_points(job: dict) -> int:
    haystack = (job.get("title", "") + " " + job.get("description", "")).lower()
    return 15 if any(kw in haystack for kw in _BONUS_KEYWORDS) else 0


def _score_job(job: dict) -> dict:
    if _check_dealbreakers(job):
        return {"score": 0, "reasons": [], "red_flags": ["dealbreaker"]}

    job_text = (
        f"Title: {job['title']}\n"
        f"Company: {job.get('company', 'Unknown')}\n"
        f"Salary: {job.get('salary', 'Not specified')}\n"
        f"Description: {job.get('description', '')}"
    )

    response = _client.chat.completions.create(
        model=_MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Candidate profile:\n{_PROFILE_TEXT}\n\nJob posting:\n{job_text}"},
        ],
    )

    try:
        raw = response.choices[0].message.content
        # strip control characters and markdown fences
        raw = "".join(c for c in raw if c >= " " or c in "\n\r\t")
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        score = min(100, int(result.get("score", 0)) + _bonus_points(job))
        return {
            "score": score,
            "reasons": result.get("reasons", []),
            "red_flags": result.get("red_flags", []),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse score response: {e}")
        return {"score": 0, "reasons": [], "red_flags": ["parse error"]}


def match_jobs(jobs: list[dict], min_score: int = 60) -> list[dict]:
    matched = []
    for job in jobs:
        result = _score_job(job)
        score = result["score"]
        label = f"{job['title']} @ {job.get('company', '?')}"
        logger.info(f"Score {score}/100 — {label}")
        if score >= min_score:
            matched.append({**job, **result})

    return sorted(matched, key=lambda x: x["score"], reverse=True)
