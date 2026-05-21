import logging
import os

from openai import OpenAI

from profile import PROFILE, profile_as_text

logger = logging.getLogger(__name__)

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
_MODEL = "anthropic/claude-3.5-haiku"

_hooks = "\n".join(f"- {h}" for h in PROFILE["cover_letter_hooks"])

_projects = "\n".join(
    f"- {p['name']}: {p['description']}"
    + (f" | Eval: {p['eval_score']}" if "eval_score" in p else "")
    for p in PROFILE["projects"]
)

_core_skills = "\n".join(
    f"- {k}: {v}" for k, v in list(PROFILE["core_skills"].items())[:12]
)

_not_my_skills = ", ".join(PROFILE["not_my_skills"])

_SYSTEM = f"""You write cover letters for {PROFILE['name']}, a Berlin-based AI engineering Werkstudent.

VOICE: Direct, confident, specific. Sound like someone who has shipped production code, not a student hoping for a chance. No "I am writing to express my interest." No corporate padding. Lead with value.

HARD RULES:
- Max 300 words
- Open by connecting a specific production achievement to their stated need
- Reference at least 2 real numbers from this list: 94.2% eval score, 100% eval score (10/10 test cases), 38% token cost reduction, 6 Docker containers, 5+ PM2 processes, 8 Supabase tables, 3 production projects
- Match 2-3 skills from the job description to ACTUAL work in the projects below — be specific about which bot or system used which technology
- Do NOT claim any skill from this list: {_not_my_skills}
- Return ONLY the cover letter body (no subject line, no "Dear...", no sign-off)

CANDIDATE FACTS:
- {PROFILE['university']} — {PROFILE['degree']}, {PROFILE['semester']}
- Availability: {PROFILE['availability']} | {PROFILE['role_type']} | {PROFILE['visa_status']}
- Works night shifts at Wilmina Hotel (100 hrs/month) while studying full-time and building 3 production AI systems
- German: A2 — roles must not require C1/C2

HOOKS — use the 1-2 most relevant to this specific job:
{_hooks}

PROJECTS WITH PROOF:
{_projects}

CORE SKILLS WITH CONTEXT:
{_core_skills}
"""

_PROFILE_TEXT = profile_as_text()


def write_cover_letter(job: dict) -> str | None:
    description = job.get("description", "")
    if len(description.split()) < 30:
        logger.warning(
            f"Skipping cover letter — description too short: "
            f"{job['title']} @ {job.get('company', '?')}"
        )
        return None

    job_text = (
        f"Role: {job['title']}\n"
        f"Company: {job.get('company', 'Unknown')}\n"
        f"Salary: {job.get('salary', 'Not specified')}\n"
        f"Matched skills: {', '.join(job.get('matched_skills', []))}\n"
        f"Description: {description}"
    )

    response = _client.chat.completions.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Candidate profile:\n{_PROFILE_TEXT}\n\n"
                    f"Write a cover letter for this job:\n{job_text}"
                ),
            },
        ],
    )

    letter = response.choices[0].message.content.strip()
    logger.info(
        f"Cover letter written: {job['title']} @ {job.get('company', '?')} "
        f"({len(letter.split())} words)"
    )
    return letter
