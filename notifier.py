import logging
import os
import re

from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

# All chars that must be escaped in MarkdownV2 plain text
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


def _format_digest(jobs: list[dict]) -> str:
    if not jobs:
        return "No new matching jobs found today\\."

    lines = ["*CV\\-Job\\-Hunter \\| Morning Digest*\n"]
    for i, job in enumerate(jobs[:3], 1):
        title = _esc(job["title"])
        company = _esc(job.get("company", "Unknown"))
        score = job.get("score", 0)
        salary = _esc(job.get("salary", ""))
        url = job.get("url", "")
        reasons = job.get("reasons", [])

        lines.append(f"*{i}\\. {title}*")
        lines.append(f"   {_esc('🏢')} {company}")
        lines.append(f"   Fit: {score}/100")
        if salary:
            lines.append(f"   {salary}")
        if reasons:
            lines.append(f"   {_esc(reasons[0])}")
        lines.append(f"   [View job]({url})")
        lines.append("")

    total = len(jobs)
    s = "es" if total != 1 else ""
    lines.append(f"_{_esc(f'{total} total match{s} today. Cover letters saved to Supabase.')}_")
    return "\n".join(lines)


async def _send_async(message: str):
    bot = _bot()
    await bot.send_message(
        chat_id=_chat_id(),
        text=message,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def send_digest(jobs: list[dict]):
    message = _format_digest(jobs)
    await _send_async(message)
    top = min(len(jobs), 3)
    logger.info(f"Telegram digest sent (top {top} of {len(jobs)} matches)")
