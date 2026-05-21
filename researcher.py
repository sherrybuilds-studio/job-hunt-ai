"""researcher.py — find open roles and hiring contacts for a target company.

Primary: direct domain probing (no search engine, no rate limits).
Secondary: DuckDuckGo HTML endpoint (retried with backoff on 202).
Screenshots: attempted with Playwright; silently skipped if system deps missing
            (fix: sudo playwright install-deps chromium).
"""

import argparse
import json
import logging
import random
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup

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
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)

_JOB_PATTERN = re.compile(
    r"(werkstudent|working student|junior|senior|engineer|developer|"
    r"manager|lead|intern|praktikant|\bai\b|\bml\b|\bllm\b|python|"
    r"backend|full.?stack|software|product|data scientist|machine learning)",
    re.I,
)

# DDG: minimum gap between requests; max retries on 202
_DDG_DELAY = 4.0
_DDG_RETRIES = 1      # 1 try only — DDG recovers within an hour if IP-blocked
_DDG_BACKOFF = 5.0

_SKIP_DOMAINS = re.compile(
    r"google\.|glassdoor\.|linkedin\.|xing\.|indeed\.|stepstone\.|"
    r"kununu\.|bing\.|yahoo\.|karriere\.|duckduckgo\.",
    re.I,
)
_CAREERS_PATH = re.compile(
    r"/(careers|jobs|arbeiten|open.?positions|stellenangebote|openings|join-us|join_us|work-with-us|join)(/|$)",
    re.I,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _domain(url: str) -> str | None:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else None


def _origin(url: str) -> str | None:
    m = re.match(r"(https?://[^/]+)", url or "")
    return m.group(1) if m else None


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=httpx.Timeout(20.0),
    )


def _fetch(client: httpx.Client, url: str) -> BeautifulSoup | None:
    try:
        resp = client.get(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.debug(f"Fetch failed {url}: {e}")
        return None


def _head_ok(client: httpx.Client, url: str) -> bool:
    """Return True if url responds with 2xx or 3xx (content exists)."""
    try:
        r = client.head(url, timeout=8)
        return r.status_code < 400
    except Exception:
        return False


# ─── Direct domain probing ────────────────────────────────────────────────────

def _domain_candidates(company: str) -> list[str]:
    """
    Generate likely domain names from a company name.
    Returns a list of bare domain strings (no scheme), priority-ordered.
    """
    # Normalise: lowercase, strip "AI" / "GmbH" / "Dr." suffixes for base slug
    clean = re.sub(r"\b(gmbh|ug|ag|ltd|inc|llc|co\.?|dr\.?)\b", "", company, flags=re.I)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Build short slug (no spaces, no dots): "CognitX AI" → "cognitx"  "KEA" → "kea"
    words = clean.lower().split()
    ai_suffixed = "ai" in words
    base_words = [w for w in words if w not in ("ai", "the", "a", "an")]
    slug = "".join(re.sub(r"[^a-z0-9]", "", w) for w in base_words)
    first_word = re.sub(r"[^a-z0-9]", "", base_words[0]) if base_words else slug
    hyphen = "-".join(re.sub(r"[^a-z0-9]", "", w) for w in base_words)

    tlds = [".ai", ".com", ".de", ".io", ".co"]
    candidates: list[str] = []

    if ai_suffixed:
        for tld in tlds:
            candidates.append(f"{slug}{tld}")
            if slug != first_word:
                candidates.append(f"{first_word}{tld}")
    for tld in tlds:
        candidates.append(f"{slug}{tld}")
    if hyphen != slug:
        for tld in tlds:
            candidates.append(f"{hyphen}{tld}")
    if first_word != slug:
        for tld in tlds:
            candidates.append(f"{first_word}{tld}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _probe_website(client: httpx.Client, company: str) -> str | None:
    """Try domain candidates and return the first live website URL."""
    for dom in _domain_candidates(company):
        url = f"https://{dom}"
        if _head_ok(client, url):
            logger.info(f"Website found: {url}")
            return url
        url_www = f"https://www.{dom}"
        if _head_ok(client, url_www):
            logger.info(f"Website found: {url_www}")
            return url_www
    return None


_CAREERS_PATHS = [
    "/careers", "/jobs", "/join", "/open-positions", "/openings",
    "/work-with-us", "/join-us", "/arbeiten", "/stellenangebote",
    "/about/careers", "/company/careers", "/en/careers", "/en/jobs",
]


def _probe_careers(client: httpx.Client, website: str) -> str | None:
    """Try known careers URL patterns against the website origin."""
    origin = _origin(website) or website.rstrip("/")
    for path in _CAREERS_PATHS:
        url = origin + path
        if _head_ok(client, url):
            logger.info(f"Careers page found: {url}")
            return url
    # Also check if the homepage itself is a careers/jobs page
    soup = _fetch(client, origin)
    if soup:
        # Look for a link on the homepage that goes to a careers page
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if _CAREERS_PATH.search(href):
                full = href if href.startswith("http") else origin + href.rstrip("/")
                return full
    return None


# ─── DuckDuckGo search (HTML endpoint, secondary) ─────────────────────────────

_last_ddg_ts: float = 0.0


def _search(client: httpx.Client, query: str) -> list[dict]:
    """
    POST to DuckDuckGo HTML endpoint. Returns [{title, url, snippet}].
    Retries up to _DDG_RETRIES times on 202 with backoff. Returns [] on failure.
    """
    global _last_ddg_ts

    for attempt in range(_DDG_RETRIES):
        elapsed = time.monotonic() - _last_ddg_ts
        wait = _DDG_DELAY + attempt * _DDG_BACKOFF - elapsed
        if wait > 0:
            logger.debug(f"DDG pause {wait:.1f}s (attempt {attempt+1})")
            time.sleep(wait + random.uniform(0.5, 1.5))

        logger.info(f"DDG search (attempt {attempt+1}): {query}")
        try:
            resp = client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "kl": "us-en"},
                headers={**_HEADERS, "Content-Type": "application/x-www-form-urlencoded",
                         "Referer": "https://duckduckgo.com/"},
            )
            _last_ddg_ts = time.monotonic()
        except Exception as e:
            logger.warning(f"DDG request error: {e}")
            continue

        if resp.status_code == 202:
            logger.warning(f"DDG 202 rate-limited (attempt {attempt+1}/{_DDG_RETRIES})")
            continue
        if not resp.is_success:
            logger.warning(f"DDG HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []
        for item in soup.select(".result"):
            title_a = item.select_one(".result__title a")
            if not title_a:
                continue
            url = _resolve_ddg_href(title_a.get("href", ""))
            if not url:
                continue
            snip_el = item.select_one(".result__snippet")
            results.append({
                "title": title_a.get_text(" ", strip=True),
                "url": url,
                "snippet": snip_el.get_text(" ", strip=True) if snip_el else "",
            })
        logger.info(f"  → {len(results)} results")
        return results

    logger.warning(f"DDG exhausted retries for: {query}")
    return []


def _resolve_ddg_href(raw: str) -> str:
    if not raw:
        return ""
    if raw.startswith("//duckduckgo.com/l/"):
        uddg = parse_qs(urlparse("https:" + raw).query).get("uddg", [""])
        return unquote(uddg[0]) if uddg[0] else ""
    if raw.startswith("http"):
        return raw
    return ""


# ─── Step 1: find careers page ────────────────────────────────────────────────

def _find_careers(
    client: httpx.Client, company: str
) -> tuple[str | None, str | None, list[str], str | None]:
    """Returns (website, careers_url, open_roles, screenshot_path)."""

    # ── Direct probing (primary) ─────────────────────────────────────────────
    website = _probe_website(client, company)
    careers_url = None
    if website:
        careers_url = _probe_careers(client, website)
        if not careers_url:
            careers_url = website   # homepage may list jobs

    # ── DDG fallback ─────────────────────────────────────────────────────────
    if not website:
        logger.info("Direct probe found nothing — trying DDG")
        results = _search(client, f"{company} careers berlin")
        for r in results:
            u = r["url"]
            if not u or _SKIP_DOMAINS.search(u):
                continue
            if _CAREERS_PATH.search(u):
                careers_url = u
                website = _origin(u)
                break
        if not careers_url:
            for r in results:
                u = r["url"]
                if u and not _SKIP_DOMAINS.search(u):
                    careers_url = u
                    website = _origin(u)
                    break

    # ── Extract roles from careers page ──────────────────────────────────────
    open_roles: list[str] = []
    screenshot_path = None

    if careers_url:
        logger.info(f"Fetching: {careers_url}")
        soup = _fetch(client, careers_url)
        if soup:
            open_roles = _extract_roles(soup)
            logger.info(f"Roles found: {len(open_roles)}")
        screenshot_path = _try_screenshot(careers_url, company)

    return website, careers_url, open_roles, screenshot_path


def _extract_roles(soup: BeautifulSoup) -> list[str]:
    roles: list[str] = []
    seen: set[str] = set()

    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))
        if 4 < len(text) < 120 and _JOB_PATTERN.search(text) and text not in seen:
            seen.add(text)
            roles.append(text)

    for a in soup.find_all("a", href=True):
        if re.search(r"/(job|position|role|career|opening)", a.get("href", ""), re.I):
            text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            if 4 < len(text) < 120 and _JOB_PATTERN.search(text) and text not in seen:
                seen.add(text)
                roles.append(text)

    return roles[:20]


def _try_screenshot(url: str, company: str) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA, viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            path = str(_DATA_DIR / f"{_slug(company)}_careers.png")
            page.screenshot(path=path, full_page=True)
            ctx.close()
            browser.close()
            logger.info(f"Screenshot: {path}")
            return path
    except Exception as e:
        logger.debug(f"Screenshot skipped: {e}")
        return None


# ─── Step 2: find contacts ────────────────────────────────────────────────────

_TEAM_PATHS = [
    "/about", "/team", "/people", "/company", "/about-us",
    "/about/team", "/en/about", "/en/team", "/company/team",
    "/management", "/leadership", "/founders",
]

_TITLE_PATTERN = re.compile(
    r"\b(cto|ceo|coo|vp|head of|director|founder|co-founder|"
    r"lead engineer|engineering lead|engineering manager|"
    r"hiring|talent|recruiter|hr)\b",
    re.I,
)


def _find_contacts(
    client: httpx.Client, company: str, website: str | None
) -> list[dict]:
    domain = _domain(website) if website else None
    contacts: list[dict] = []
    seen_names: set[str] = set()

    # ── Scrape About/Team page (primary) ─────────────────────────────────────
    if website:
        origin = _origin(website) or website.rstrip("/")
        for path in _TEAM_PATHS:
            url = origin + path
            soup = _fetch(client, url)
            if not soup:
                continue
            new = _extract_contacts_from_page(soup, domain, seen_names)
            if new:
                contacts.extend(new)
                logger.info(f"Found {len(new)} contacts from {url}")
                break   # stop at first page with results

    # ── DDG LinkedIn search (secondary) ──────────────────────────────────────
    if len(contacts) < 2:
        queries = [
            f"{company} CTO site:linkedin.com",
            f"{company} Head of Engineering site:linkedin.com",
            f"{company} hiring AI site:linkedin.com",
        ]
        seen_urls: set[str] = set()
        for query in queries:
            for r in _search(client, query):
                url = r.get("url", "")
                if "linkedin.com/in/" not in url or url in seen_urls:
                    continue
                seen_urls.add(url)
                name, title = _parse_linkedin_title(r.get("title", ""), company)
                if not name or name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())
                contacts.append({
                    "name": name,
                    "title": title,
                    "linkedin": url,
                    "guessed_email": _guess_email(name, domain),
                })

    return contacts


def _extract_contacts_from_page(
    soup: BeautifulSoup, domain: str | None, seen_names: set[str]
) -> list[dict]:
    contacts: list[dict] = []

    # Look for LinkedIn profile links on the page
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "linkedin.com/in/" not in href:
            continue
        # Try to find a name and title near this link
        parent = a.parent
        text_block = parent.get_text(" ", strip=True) if parent else ""

        # Also check grandparent for richer context
        if len(text_block) < 10 and parent and parent.parent:
            text_block = parent.parent.get_text(" ", strip=True)

        name, title = _extract_name_title_from_block(text_block)
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        contacts.append({
            "name": name,
            "title": title,
            "linkedin": href if href.startswith("http") else "https://" + href.lstrip("/"),
            "guessed_email": _guess_email(name, domain),
        })

    # If no LinkedIn links, try to extract names+titles from headings
    if not contacts:
        for heading in soup.find_all(["h2", "h3", "h4"]):
            heading_text = heading.get_text(" ", strip=True)
            if not heading_text or len(heading_text) > 60:
                continue
            # sibling paragraphs often have the title
            sibling = heading.find_next_sibling(["p", "span", "div"])
            title_text = sibling.get_text(" ", strip=True) if sibling else ""
            if _TITLE_PATTERN.search(title_text) or _TITLE_PATTERN.search(heading_text):
                name = heading_text
                title = title_text if _TITLE_PATTERN.search(title_text) else heading_text
                if name.lower() not in seen_names and len(name.split()) >= 2:
                    seen_names.add(name.lower())
                    contacts.append({
                        "name": name,
                        "title": title,
                        "linkedin": None,
                        "guessed_email": _guess_email(name, domain),
                    })

    return contacts


def _extract_name_title_from_block(text: str) -> tuple[str, str]:
    """Try to pull a name and title out of a short text block."""
    lines = [l.strip() for l in re.split(r"[\n|·•]", text) if l.strip()]
    if not lines:
        return "", ""
    # First non-empty line is usually the name
    name = lines[0] if len(lines[0].split()) <= 5 else ""
    title = ""
    for line in lines[1:3]:
        if _TITLE_PATTERN.search(line):
            title = line
            break
    return name, title


def _parse_linkedin_title(text: str, company: str) -> tuple[str, str]:
    """Parse 'Jane Doe - CTO at KEA | LinkedIn' → ('Jane Doe', 'CTO')."""
    clean = re.sub(r"\s*\|?\s*LinkedIn\s*$", "", text, flags=re.I).strip()
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
    parts = [re.sub(r"[^a-z]", "", p) for p in name.lower().split() if re.sub(r"[^a-z]", "", p)]
    if not parts:
        return None
    return f"{parts[0]}.{parts[-1]}@{domain}" if len(parts) >= 2 else f"{parts[0]}@{domain}"


# ─── Step 3: email pattern ────────────────────────────────────────────────────

_CONTACT_PATHS = ["/contact", "/contact-us", "/impressum", "/imprint", "/legal", "/about/contact"]
_CAREERS_PREFIXES = ("jobs@", "careers@", "hiring@", "talent@", "work@", "hr@", "apply@", "hello@")


def _find_email_pattern(
    client: httpx.Client, company: str, website: str | None
) -> tuple[str | None, str | None]:
    """Returns (email_pattern, careers_email)."""
    domain = _domain(website) if website else None
    careers_email = None
    email_pattern = f"first.last@{domain}" if domain else None

    # ── Scrape contact/impressum pages (primary) ──────────────────────────────
    if website:
        origin = _origin(website) or website.rstrip("/")
        for path in _CONTACT_PATHS:
            soup = _fetch(client, origin + path)
            if not soup:
                continue
            for email in _EMAIL_RE.findall(soup.get_text(" ")):
                el = email.lower()
                if any(el.startswith(p) for p in _CAREERS_PREFIXES):
                    careers_email = el
                    logger.info(f"Found careers email: {careers_email}")
                    break
                if domain and el.endswith(f"@{domain}") and not careers_email:
                    careers_email = el
            if careers_email:
                break

    # ── DDG search (secondary) ────────────────────────────────────────────────
    if not careers_email:
        results = _search(client, f'"{company}" email format OR jobs@ OR careers@')
        for r in results:
            for email in _EMAIL_RE.findall(r.get("snippet", "") + " " + r.get("title", "")):
                el = email.lower()
                if any(el.startswith(p) for p in _CAREERS_PREFIXES):
                    careers_email = el
                    break
                if domain and el.endswith(f"@{domain}") and not careers_email:
                    careers_email = el
            if careers_email:
                break

    # Refine pattern via hunter.io snippet
    if domain:
        for r in _search(client, f"site:hunter.io {domain}"):
            m = re.search(r"(first\.last|first_last|f\.last|flast|first)\b", r.get("snippet", ""), re.I)
            if m:
                email_pattern = f"{m.group(1).lower()}@{domain}"
                break

    return email_pattern, careers_email


# ─── main pipeline ────────────────────────────────────────────────────────────

def research_company(company: str) -> dict:
    logger.info("=" * 60)
    logger.info(f"Researching: {company}")
    logger.info("=" * 60)
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

    with _make_client() as client:
        try:
            website, careers_url, open_roles, screenshot = _find_careers(client, company)
            result.update(website=website, careers_page=careers_url,
                          open_roles=open_roles, screenshot=screenshot)

            contacts = _find_contacts(client, company, website)
            result["contacts"] = contacts
            logger.info(f"Contacts: {len(contacts)}")

            email_pattern, careers_email = _find_email_pattern(client, company, website)
            result.update(email_pattern=email_pattern, careers_email=careers_email)

        except Exception as e:
            logger.error(f"Pipeline error for {company}: {e}")

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
            c = job.get("company", "").strip()
            if c and c.lower() not in seen:
                seen.add(c.lower())
                companies.append(c)
    logger.info(f"Batch: {len(companies)} unique companies from top_matches.json")
    return companies


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Research hiring contacts and open roles for a company"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--company", metavar="NAME", help='e.g. "KEA"')
    group.add_argument("--batch", action="store_true", help="All companies from top_matches.json")
    args = parser.parse_args()

    if args.batch:
        companies = _batch_companies()
        if not companies:
            return
        for company in companies:
            try:
                r = research_company(company)
                print(
                    f"  ✓ {r['company']:<32} "
                    f"{len(r['contacts'])} contacts  "
                    f"{len(r['open_roles'])} roles  "
                    f"screenshot={'yes' if r['screenshot'] else 'no'}"
                )
            except Exception as e:
                logger.error(f"Failed {company}: {e}")
    else:
        result = research_company(args.company)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
