import logging

from profile import PROFILE

logger = logging.getLogger(__name__)

# Terms derived from PROFILE["not_my_skills"] — checked against job titles.
# Short ambiguous names (R, Go) get padded with spaces so they only match as
# whole words against the space-padded title string.
_NOT_MY_SKILL_TERMS: list[str] = []
for _s in PROFILE["not_my_skills"]:
    _t = _s.lower()
    if _t in ("r", "go"):
        _NOT_MY_SKILL_TERMS.append(f" {_t} ")
    else:
        _NOT_MY_SKILL_TERMS.append(_t)

# Job must mention at least one of these to pass the must-have filter
MUST_HAVE = [
    "werkstudent", "working student", "internship", "part-time student",
    "student assistant", "studentische", "hiwi", "teilzeit",
    "part time", "studentenjob", "student job", " intern ",
]

# (keywords_to_match, points, display_label) — max total = 105
SKILL_WEIGHTS: list[tuple[list[str], int, str]] = [
    (["python"], 20, "Python"),
    (["llm", "claude", "openai", "ai agent", "language model", "gpt", "large language"], 20, "LLM/AI"),
    (["rag", "vector", "chromadb", "embedding", "retrieval augmented", "vector store"], 15, "RAG/Vectors"),
    (["fastapi", "flask", " api ", "rest api", "api development"], 10, "FastAPI/API"),
    (["n8n", "automation", "workflow", "zapier", "process automation"], 15, "n8n/Automation"),
    (["whatsapp", "meta api", "messaging", "telegram bot", "chatbot", "conversational"], 10, "WhatsApp/Messaging"),
    (["docker", "linux", "vps", "devops", "kubernetes", "cloud deployment", "server deploy"], 10, "Docker/DevOps"),
    (["supabase", "postgresql", "postgres", "database", "mysql", " sql "], 5, "Supabase/DB"),
]

_GERMAN_REQUIRED = [
    "deutsch c1", "deutsch c2", "c1 deutsch", "c2 deutsch",
    "german c1", "german c2", "deutschkenntnisse c1", "deutschkenntnisse c2",
    "verhandlungssicheres deutsch", "fließendes deutsch",
    "german native", "native german",
]

# Rough heuristic: 4+ of these common German function words → listing is in German
_GERMAN_MARKERS = [
    " wir ", " sie ", " ihr ", " haben ", " werden ", " und ",
    " oder ", " für ", " mit ", " sind ", " die ", " der ", " das ",
]


def _passes_must_have(job: dict) -> bool:
    haystack = (job.get("title", "") + " " + job.get("description", "")).lower()
    return any(kw in haystack for kw in MUST_HAVE)


def _score_job(job: dict) -> dict:
    # Pad with spaces so whole-word substring checks work without regex
    haystack = " " + (job.get("title", "") + " " + job.get("description", "")).lower() + " "

    score = 0
    matched_skills: list[str] = []
    missing_skills: list[str] = []

    for keywords, weight, label in SKILL_WEIGHTS:
        if any(kw in haystack for kw in keywords):
            score += weight
            matched_skills.append(label)
        else:
            missing_skills.append(label)

    # Language adjustment: −20 if German C1/C2 required, +10 if English listing
    if any(p in haystack for p in _GERMAN_REQUIRED):
        score -= 20
        missing_skills.append("German C1/C2 required")
        red_flags = ["German C1/C2 required"]
    else:
        german_word_count = sum(1 for m in _GERMAN_MARKERS if m in haystack)
        if german_word_count < 4:
            score += 10
            matched_skills.append("English listing")
        red_flags = []

    # Not-my-skills penalty: −15 per term found in the job title (cap −30).
    # Title is the clearest signal that a skill is the primary requirement.
    title_padded = " " + job.get("title", "").lower() + " "
    not_my_penalty = 0
    for term in _NOT_MY_SKILL_TERMS:
        if term in title_padded and not_my_penalty < 30:
            not_my_penalty += 15
            missing_skills.append(f"Title requires {term.strip()} (not my stack)")
    score -= not_my_penalty

    return {
        "score": max(0, score),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "reasons": matched_skills[:3],
        "red_flags": red_flags,
    }


def match_jobs(jobs: list[dict], min_score: int = 40) -> list[dict]:
    matched = []
    for job in jobs:
        label = f"{job['title']} @ {job.get('company', '?')}"

        if not _passes_must_have(job):
            logger.debug(f"Filtered (no werkstudent/intern): {label}")
            continue

        result = _score_job(job)
        score = result["score"]
        logger.info(f"Score {score}/105 — {label}")

        if score >= min_score:
            matched.append({**job, **result})

    return sorted(matched, key=lambda x: x["score"], reverse=True)
