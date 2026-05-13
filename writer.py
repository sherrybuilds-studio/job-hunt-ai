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

_SYSTEM = f"""You write professional cover letters for {MY_PROFILE.name.split(' (')[0]}, an AI developer in Berlin.

Rules:
- Max 300 words
- Open directly with the role and what you bring — no "I am writing to express my interest"
- Reference 2-3 skills most relevant to THIS specific job description
- Mention the luxury interior brand AI system project when it fits the job
- Only mention salary ({MY_PROFILE.salary_range}) if the job listing specifies a range
- Sound confident, direct, and human — not corporate
- Return ONLY the cover letter body text (no subject line, no salutation header)"""


def write_cover_letter(job: dict) -> str | None:
    description = job.get("description", "")
    if len(description.split()) < 30:
        logger.warning(f"Skipping cover letter — description too short: {job['title']} @ {job.get('company', '?')}")
        return None

    job_text = (
        f"Role: {job['title']}\n"
        f"Company: {job.get('company', 'Unknown')}\n"
        f"Salary: {job.get('salary', 'Not specified')}\n"
        f"Description: {description}"
    )

    response = _client.chat.completions.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"My profile:\n{_PROFILE_TEXT}\n\nWrite a cover letter for this job:\n{job_text}"},
        ],
    )

    letter = response.choices[0].message.content.strip()
    logger.info(f"Cover letter written for: {job['title']} @ {job.get('company', '?')} ({len(letter.split())} words)")
    return letter
