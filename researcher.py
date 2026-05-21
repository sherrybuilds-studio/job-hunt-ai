"""researcher.py — find open roles and hiring contacts for a target company."""

import argparse
import json
import logging
import os
import random
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import Page, sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("researcher")

_TODAY = date.today().isoformat()
_DATA_DIR = Path(__file__).parent / "data" / "companies"

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_DELAY_MIN = 3.0
_DELAY_MAX = 5.5

# Regex matching text that looks like a job title
_JOB_PATTERN = re.compile(
    r"(werkstudent|working student|junior|senior|engineer|developer|"
    r"manager|lead|intern|praktikant|\bai\b|\bml\b|\bllm\b|python|"
    r"backend|full.?stack|software|product|data scientist|machine learning)",
    re.I,
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _pause():
    t = random.uniform(_DELAY_MIN, _DELAY_MAX)
    logger.debug(f"Sleeping {t:.1f}s")
    time.sleep(t)


def _domain(url: str) -> str | None:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else None


def _origin(url: str) -> str | None:
    m = re.match(r"(https?://[^/]+)", url or "")
    return m.group(1) if m else None


def _accept_consent(page: Page):
    """Click through Google's EU cookie consent wall if present."""
    try:
        for selector in [
            "button:has-text('Accept all')",
            "button:has-text('Ich stimme zu')",
            "button:has-text('Alles akzeptieren')",
            "[aria-label='Accept all']",
        ]:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(1)
                logger.debug("Accepted Google consent")
                return
    except Exception:
        pass


# ─── Google search ────────────────────────────────────────────────────────────

def _google(page: Page, query: str) -> list[dict]:
    """
    Run a Google search and return up to 8 results as
    [{title, url, snippet}]. Never raises — returns [] on failure.
    """
    search_url = (
        f"https://www.google.com/search"
        f"?q={query.replace(' ', '+')}&hl=en&gl=de&num=10"
    )
    logger.info(f"Google: {query}")
    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(1.5)
        _accept_consent(page)
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Google navigation error: {e}")
        return []

    results: list[dict] = []

    # Try progressively broader container selectors
    for container_sel in ("div.g", "div.tF2Cxc", "div[data-sokoban-container]", "li.g"):
        containers = page.query_selector_all(container_sel)
        if not containers:
            continue
        for el in containers[:8]:
            try:
                h3 = el.query_selector("h3")
                title = h3.inner_text().strip() if h3 else ""

                link = el.query_selector("a[href]")
                raw_href = link.get_attribute("href") if link else ""
                url = _resolve_google_href(raw_href)

                # Several possible snippet selectors
                snippet = ""
                for snip_sel in ("div.VwiC3b", "span.aCOpRe", "div[data-sncf='1']", "div.s"):
                    snip_el = el.query_selector(snip_sel)
                    if snip_el:
                        snippet = snip_el.inner_text().strip()
                        break

                if title or url:
                    results.append({"title": title, "url": url, "snippet": snippet})
            except Exception:
                pass
        if results:
            break

    # Last-resort: find all links on the page that aren't Google-internal
    if not results:
        for a in page.query_selector_all("a[href]"):
            try:
                href = _resolve_google_href(a.get_attribute("href") or "")
                if href and "google." not in href and href.startswith("http"):
                    text = a.inner_text().strip()
                    if text:
                        results.append({"title": text, "url": href, "snippet": ""})
            except Exception:
                pass
        results = results[:8]

    logger.debug(f"  → {len(results)} results")
    return results


def _resolve_google_href(raw: str) -> str:
    """Convert Google redirect URLs to the real destination URL."""
    if not raw:
        return ""
    if raw.startswith("/url?") or raw.startswith("https://www.google.com/url?"):
        m = re.search(r"[?&]q=([^&]+)", raw)
        if m:
            return unquote(m.group(1))
    if raw.startswith("http"):
        return raw
    return ""


# ─── Step 1: careers page ─────────────────────────────────────────────────────

_SKIP_DOMAINS = re.compile(
    r"google\.|glassdoor\.|linkedin\.|xing\.|indeed\.|stepstone\.|"
    r"kununu\.|bing\.|yahoo\.|karriere\.",
    re.I,
)

_CAREERS_PATH = re.compile(
    r"/(careers|jobs|arbeiten|open.positions|stellenangebote|openings|join.us|"
    r"join-us|work-with-us|join)",
    re.I,
)


def _find_careers(page: Page, company: str) -> tuple[str | None, str | None, list[str], str | None]:
    """
    Returns (website, careers_url, open_roles, screenshot_path).
    Searches Google, picks the best careers URL, visits it, screenshots, extracts roles.
    """
    results = _google(page, f"{company} careers berlin")
    _pause()

    website = None
    careers_url = None

    # Priority 1: explicit careers/jobs path, not a job board
    for r in results:
        url = r["url"]
        if not url or _SKIP_DOMAINS.search(url):
            continue
        if _CAREERS_PATH.search(url):
            careers_url = url
            website = _origin(url)
            break

    # Priority 2: any non-job-board result
    if not careers_url:
        for r in results:
            url = r["url"]
            if url and not _SKIP_DOMAINS.search(url):
                careers_url = url
                website = _origin(url)
                break

    open_roles: list[str] = []
    screenshot_path = None

    if careers_url:
        try:
            logger.info(f"Visiting careers page: {careers_url}")
            page.goto(careers_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            screenshot_path = str(_DATA_DIR / f"{_slug(company)}_careers.png")
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot: {screenshot_path}")

            open_roles = _extract_roles(page)
            logger.info(f"Roles found: {len(open_roles)}")
        except Exception as e:
            logger.error(f"Error visiting {careers_url}: {e}")

    return website, careers_url, open_roles, screenshot_path


def _extract_roles(page: Page) -> list[str]:
    """Extract job-title-like text from the current page."""
    roles: list[str] = []
    seen: set[str] = set()

    # Headings first (most reliable), then job-path links
    for sel in ("h1, h2, h3, h4", "a[href*='job'], a[href*='position'], a[href*='role']"):
        for el in page.query_selector_all(sel):
            try:
                text = re.sub(r"\s+", " ", el.inner_text().strip())
                if 4 < len(text) < 120 and _JOB_PATTERN.search(text) and text not in seen:
                    seen.add(text)
                    roles.append(text)
            except Exception:
                pass

    return roles[:20]


# ─── Step 2: contacts ─────────────────────────────────────────────────────────

def _find_contacts(page: Page, company: str, website: str | None) -> list[dict]:
    """Search Google for LinkedIn profiles of hiring contacts."""
    domain = _domain(website) if website else None

    queries = [
        f"{company} CTO site:linkedin.com",
        f"{company} Head of Engineering site:linkedin.com",
        f"{company} hiring manager AI site:linkedin.com",
    ]

    contacts: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        results = _google(page, query)
        _pause()

        for r in results:
            url = r.get("url", "")
            if "linkedin.com/in/" not in url or url in seen_urls:
                continue
            seen_urls.add(url)

            name, title = _parse_linkedin_title(r.get("title", ""), company)
            if not name:
                continue

            contacts.append({
                "name": name,
                "title": title,
                "linkedin": url,
                "guessed_email": _guess_email(name, domain),
            })

    return contacts


def _parse_linkedin_title(text: str, company: str) -> tuple[str, str]:
    """
    Parse Google result titles like:
      'Jane Doe - CTO at KEA | LinkedIn'
      'John Smith – Head of Engineering | LinkedIn'
    Returns (name, role_title).
    """
    # Strip trailing '| LinkedIn'
    clean = re.sub(r"\s*\|?\s*LinkedIn\s*$", "", text, flags=re.I).strip()

    # "Name - Title at Company" or "Name – Title"
    m = re.match(r"^([A-Z][^-–|]{1,40}?)\s*[-–]\s*(.+?)(?:\s+at\s+.+)?$", clean)
    if m:
        name = m.group(1).strip()
        role = re.sub(rf"\s+at\s+{re.escape(company)}.*$", "", m.group(2), flags=re.I).strip()
        return name, role

    parts = re.split(r"\s*[-–|]\s*", clean, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    return clean, ""


def _guess_email(name: str, domain: str | None) -> str | None:
    if not domain:
        return None
    parts = [re.sub(r"[^a-z]", "", p) for p in name.lower().split()]
    parts = [p for p in parts if p]
    if not parts:
        return None
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[-1]}@{domain}"
    return f"{parts[0]}@{domain}"


# ─── Step 3: email pattern ────────────────────────────────────────────────────

def _find_email_pattern(
    page: Page, company: str, website: str | None
) -> tuple[str | None, str | None]:
    """Returns (email_pattern, careers_email)."""
    domain = _domain(website) if website else None

    # Search for any public email references
    results = _google(page, f'"{company}" email format OR jobs@ OR careers@')
    _pause()

    careers_email = None
    email_pattern = f"first.last@{domain}" if domain else None

    careers_prefixes = ("jobs@", "careers@", "hiring@", "talent@", "work@", "hr@", "apply@")

    for r in results:
        for email in _EMAIL_RE.findall(r.get("snippet", "") + " " + r.get("title", "")):
            el = email.lower()
            if any(el.startswith(p) for p in careers_prefixes):
                careers_email = el
                break
            if domain and el.endswith(f"@{domain}") and not careers_email:
                careers_email = el
        if careers_email:
            break

    # Refine pattern from hunter.io snippets if available
    if domain:
        hunter_results = _google(page, f"site:hunter.io {domain}")
        _pause()
        pattern_re = re.compile(r"(first\.last|first_last|f\.last|flast|first)\b", re.I)
        for r in hunter_results:
            m = pattern_re.search(r.get("snippet", ""))
            if m:
                email_pattern = f"{m.group(1).lower()}@{domain}"
                break

    return email_pattern, careers_email


# ─── main pipeline ────────────────────────────────────────────────────────────

def research_company(company: str) -> dict:
    """Full research pipeline. Returns the result dict and saves JSON."""
    logger.info(f"{'='*60}")
    logger.info(f"Researching: {company}")
    logger.info(f"{'='*60}")
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    result: dict = {
        "company": company,
        "website": None,
        "careers_page": None,
        "open_roles": [],
        "contacts": [],
        "email_pattern": None,
        "careers_email": None,
        "screenshot": None,
        "researched_date": _TODAY,
    }

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as e:
            if "shared libraries" in str(e) or "TargetClosedError" in type(e).__name__:
                logger.error(
                    "Chromium missing system libraries. Fix with:\n"
                    "  sudo playwright install-deps chromium\n"
                    "or:\n"
                    "  sudo apt-get install -y libatk1.0-0 libatk-bridge2.0-0 "
                    "libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 libatspi2.0-0"
                )
            raise
        ctx = browser.new_context(
            user_agent=_UA,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = ctx.new_page()

        try:
            # Step 1
            website, careers_url, open_roles, screenshot = _find_careers(page, company)
            result["website"] = website
            result["careers_page"] = careers_url
            result["open_roles"] = open_roles
            result["screenshot"] = screenshot

            # Step 2
            contacts = _find_contacts(page, company, website)
            result["contacts"] = contacts
            logger.info(f"Contacts: {len(contacts)}")

            # Step 3
            email_pattern, careers_email = _find_email_pattern(page, company, website)
            result["email_pattern"] = email_pattern
            result["careers_email"] = careers_email

        except Exception as e:
            logger.error(f"Pipeline error for {company}: {e}")
        finally:
            ctx.close()
            browser.close()

    out_path = _DATA_DIR / f"{_slug(company)}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved: {out_path}")

    return result


# ─── batch mode ───────────────────────────────────────────────────────────────

def _batch_companies() -> list[str]:
    json_path = Path(__file__).parent / "data" / "top_matches.json"
    if not json_path.exists():
        logger.error(f"Not found: {json_path} — run agent.py first")
        return []

    with open(json_path) as f:
        runs = json.load(f)

    seen: set[str] = set()
    companies: list[str] = []
    for run in runs:
        for job in run.get("top_10", []):
            company = job.get("company", "").strip()
            if company and company.lower() not in seen:
                seen.add(company.lower())
                companies.append(company)

    logger.info(f"Batch: {len(companies)} unique companies from top_matches.json")
    return companies


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Research hiring contacts and open roles for a company"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--company", metavar="NAME", help='Company to research, e.g. "KEA"')
    group.add_argument(
        "--batch", action="store_true", help="Research all companies from data/top_matches.json"
    )
    args = parser.parse_args()

    if args.batch:
        companies = _batch_companies()
        if not companies:
            return
        for company in companies:
            try:
                r = research_company(company)
                print(
                    f"  ✓ {r['company']:<30} "
                    f"{len(r['contacts'])} contacts  "
                    f"{len(r['open_roles'])} roles"
                )
            except Exception as e:
                logger.error(f"Failed {company}: {e}")
    else:
        result = research_company(args.company)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
