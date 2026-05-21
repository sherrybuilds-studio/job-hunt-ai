import logging
import os
import re

from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

_MD_SPECIAL = re.compile(r'([_*\[\]()~`>#+\-=|{}.!\\])')


def _esc(text: str) -> str:
    return _MD_SPECIAL.sub(r'\\\1', str(text))


def _bot() -> Bot:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment")
    return Bot(token=token)


def _chat_id() -> str:
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID must be set in environment")
    return chat_id


def _job_block_full(i: int, job: dict) -> list[str]:
    title = _esc(job["title"])
    company = _esc(job.get("company", "Unknown"))
    score = job.get("score", 0)
    salary = job.get("salary", "")
    url = job.get("url", "")
    matched = job.get("matched_skills", [])
    missing = job.get("missing_skills", [])

    lines = [f"*{i}\\. {title}*", f"   🏢 {company}   Score: {_esc(str(score))}/105"]
    if salary:
        lines.append(f"   💰 {_esc(salary)}")
    if matched:
        lines.append("   ✅ " + _esc(", ".join(matched[:4])))
    if missing:
        lines.append("   ❌ " + _esc(", ".join(missing[:3])))
    if url:
        lines.append(f"   📎 [View job]({url})")
    lines.append("")
    return lines


def _job_block_brief(i: int, job: dict) -> list[str]:
    title = _esc(job["title"])
    company = _esc(job.get("company", "Unknown"))
    score = job.get("score", 0)
    url = job.get("url", "")
    matched = job.get("matched_skills", [])

    line = f"{i}\\. *{title}* — {company} \\({_esc(str(score))}/105\\)"
    if matched:
        line += " ✅ " + _esc(", ".join(matched[:2]))
    lines = [line]
    if url:
        lines.append(f"   📎 [View]({url})")
    lines.append("")
    return lines


def _format_digest(
    jobs: list[dict],
    top5: list[dict] | None = None,
    total_scraped: int = 0,
    min_score: int = 40,
) -> str:
    lines = ["*CV\\-Job\\-Hunter \\| Morning Digest*\n"]

    # Section 1: jobs that cleared the threshold
    if jobs:
        lines.append(f"🔥 *MATCHES \\(score ≥ {_esc(str(min_score))}\\)*\n")
        for i, job in enumerate(jobs, 1):
            lines.extend(_job_block_full(i, job))
    else:
        lines.append(f"_No matches above {_esc(str(min_score))} today\\._\n")

    # Section 2: top 5 regardless of threshold
    if top5:
        lines.append("📊 *TOP 5 TODAY*\n")
        for i, job in enumerate(top5, 1):
            lines.extend(_job_block_brief(i, job))

    # Footer
    top_score = top5[0]["score"] if top5 else (jobs[0]["score"] if jobs else 0)
    lines.append(
        f"_📈 Scraped: {_esc(str(total_scraped))} \\| "
        f"Passed filter: {_esc(str(len(jobs)))} \\| "
        f"Top score: {_esc(str(top_score))}/105_"
    )
    return "\n".join(lines)


async def _send_async(message: str):
    bot = _bot()
    await bot.send_message(
        chat_id=_chat_id(),
        text=message,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def send_digest(
    jobs: list[dict],
    top5: list[dict] | None = None,
    total_scraped: int = 0,
    min_score: int = 40,
):
    message = _format_digest(jobs, top5=top5, total_scraped=total_scraped, min_score=min_score)
    await _send_async(message)
    logger.info(
        f"Telegram digest sent — {len(jobs)} matches, "
        f"top5={'yes' if top5 else 'no'}, scraped={total_scraped}"
    )
