PROFILE = {
    "name": "Muhammad Shehryar",
    "email": "shehryarmughal30@gmail.com",
    "phone": "+49 176 20964402",
    "location": "Berlin, Germany",
    "github": "github.com/sherrybuilds-studio",
    "university": "Arden University Berlin",
    "degree": "B.Sc. Computer Science",
    "semester": "1st year (2025-2028)",
    "availability": "20 hours/week",
    "role_type": "Werkstudent / Working Student",
    "citizenship": "Pakistani",
    "visa_status": "Student visa with Werkstudent permission",

    "languages": {
        "English": "Fluent",
        "Urdu": "Fluent (native)",
        "German": "A2 — actively learning",
    },

    "german_filter": "Reject roles requiring German C1/C2/fluent. Accept roles with no German requirement, or A2/B1 acceptable.",

    "core_skills": {
        "Python": "Primary language — all 3 production projects built in Python",
        "FastAPI": "Production API framework — Montari bot on port 8000, restaurant bot on port 8001",
        "Claude API": "Via OpenRouter — powers all 3 bots (claude-3.5-haiku)",
        "RAG pipelines": "Hybrid keyword + semantic search over ChromaDB with all-MiniLM-L6-v2 embeddings",
        "ChromaDB": "Vector DB — 20 furniture docs + 46 restaurant docs indexed",
        "Supabase": "PostgreSQL database — 8 tables across projects (leads, reservations, customers, waitlist, analytics)",
        "n8n": "Workflow automation — active lead pipeline running every 6 hours with Telegram alerts",
        "Meta WhatsApp Cloud API": "Production integration — webhook verified by Meta 4 times, Hello World sent",
        "Telegram Bot API": "2 bots running — dev notifications + lead alerts",
        "Docker": "Docker Compose — 6 container Langfuse stack with tuned memory limits",
        "Linux": "Ubuntu 24 VPS administration — Hostinger KVM 4 (16GB RAM, 4 vCPU, 200GB disk)",
        "PM2": "Process manager — 5+ processes running 24/7 including cron jobs",
        "Cloudflare Tunnel": "Permanent public webhook URL — replaced ngrok",
        "Tailscale": "Private VPN — SSH access to VPS from anywhere",
        "Langfuse": "Self-hosted v3 observability — traces every LLM call with cost, latency, tokens, cache hits",
        "Claude Code": "Daily use — v2.1.143 connected to VPS via Remote SSH",
        "Git/GitHub": "3 active repos — montari-oak-ai, job-hunt-ai, restaurant-bot-ai",
        "Semantic caching": "95% cosine similarity threshold — saves API calls on repeated queries",
        "Security": "HMAC-SHA256 webhook verification, slowapi rate limiting (10 req/min), input sanitization (6 injection patterns blocked), chmod 600 on all .env files",
        "Eval frameworks": "Gold-standard test suites — 94.2% on interior bot, 100% on restaurant bot",
    },

    "secondary_skills": {
        "Firecrawl": "Web scraping API — integrated into job hunter",
        "OpenClaw": "AI agent gateway — running on VPS port 18789",
        "Shopify": "Built and ran D2C lamp store for 1.5 years",
        "CRM systems": "Used in Mehboob Steels for team management",
        "E-commerce": "Marketing, inventory, financial planning experience",
    },

    "not_my_skills": [
        "React", "TypeScript", "Vue", "Angular", "frontend frameworks",
        "Java", "C++", "Go", "Rust", "Scala",
        "Kubernetes", "Terraform", "Pulumi",
        "PyTorch", "TensorFlow", "model training", "fine-tuning",
        "Data science", "statistics", "R", "Matlab", "Jupyter",
        "iOS", "Android", "mobile development",
        "Solidity", "blockchain", "web3",
    ],

    "projects": [
        {
            "name": "AI Interior Design Sales Bot",
            "description": "Multilingual WhatsApp sales agent for luxury furniture brands targeting high-net-worth buyers. Hybrid RAG pipeline with semantic caching reducing token costs by 38%.",
            "stack": ["Python", "FastAPI", "Claude 3.5 Haiku", "ChromaDB", "Supabase", "n8n", "Meta WhatsApp Cloud API", "Cloudflare Tunnel", "Langfuse"],
            "eval_score": "94.2%",
            "status": "Production — Meta API verified, Langfuse tracing live",
            "github": "montari-oak-ai",
        },
        {
            "name": "AI Restaurant Management Bot",
            "description": "End-to-end restaurant automation: reservations, waitlist, review monitoring, broadcast campaigns, daily owner reports via Telegram. Designed as €2,500 setup + €400/month product for Berlin restaurants.",
            "stack": ["FastAPI", "Claude API", "ChromaDB", "Supabase", "n8n", "Telegram Bot API"],
            "eval_score": "100% — 10/10 gold-standard test cases",
            "status": "Production ready — onboarding first client",
            "github": "restaurant-bot-ai",
        },
        {
            "name": "AI Job Hunter Agent",
            "description": "Autonomous agent running daily at 08:00 Berlin time via PM2 cron. Scrapes Berlin AI roles, scores matches, drafts cover letters with Claude, sends Telegram digest.",
            "stack": ["Python", "Adzuna API", "Firecrawl", "Claude API", "Supabase", "PM2", "Telegram Bot API"],
            "eval_score": "78 scraped, 66 matched, 0 errors per run",
            "status": "Live — running daily on cron",
            "github": "job-hunt-ai",
        },
        {
            "name": "Langfuse Observability Stack",
            "description": "Self-hosted Langfuse v3 — 6 Docker containers (web, worker, PostgreSQL, ClickHouse, Redis, MinIO) with memory limits tuned. SSH tunnel access only.",
            "stack": ["Docker Compose", "Langfuse v3", "PostgreSQL", "ClickHouse", "Redis", "MinIO"],
            "status": "Live on VPS",
        },
    ],

    "work_experience": [
        {
            "role": "Night Receptionist",
            "company": "Wilmina Hotel, Berlin",
            "period": "Jan 2025 — present",
            "detail": "100 hrs/month while studying full-time and building 3 AI projects",
        },
        {
            "role": "Operations Manager",
            "company": "Mehboob Steels (family business), Lahore",
            "period": "Jan 2022 — Nov 2024",
            "detail": "Led team of 15, implemented CRM workflows, drove revenue growth",
        },
        {
            "role": "E-Commerce Founder",
            "company": "Shopify Lamp Store",
            "period": "Jun 2023 — Nov 2024",
            "detail": "Founded D2C store — marketing, inventory, finance, customer support",
        },
        {
            "role": "Event Coordinator",
            "company": "Goldman Sachs at Hotel Adlon, Berlin",
            "period": "2024",
            "detail": "Logistics and guest management for corporate event",
        },
    ],

    "infrastructure": {
        "server": "Hostinger VPS KVM 4 — 16GB RAM, 4 vCPU, 200GB disk, Ubuntu 24",
        "processes": "PM2 managing 5+ services 24/7",
        "containers": "6 Docker containers (Langfuse stack) with memory limits",
        "tunnel": "Cloudflare Tunnel — permanent public webhook URL",
        "vpn": "Tailscale — private SSH access from anywhere",
        "monitoring": "UptimeRobot — pings /health every 5 mins, Telegram alert if down",
        "observability": "Langfuse v3 — traces every LLM call",
    },

    "target_roles": [
        "Werkstudent AI", "Working Student AI", "Working Student LLM",
        "Werkstudent Python", "Working Student Automation",
        "Werkstudent Software Engineering AI", "AI Engineering Intern",
    ],

    "target_companies": "Small startups (under 50 people), remote-first, English working language, Berlin or EU remote. AI/LLM/automation focus preferred.",

    "cover_letter_hooks": [
        "Built 3 production AI systems in 3 weeks — not tutorials, real deployed code",
        "Meta verified my WhatsApp webhook 4 times — the bot is live",
        "Restaurant bot scored 100% on eval — 10/10 gold standard test cases",
        "I manage my own VPS with 6 Docker containers, PM2, and Langfuse tracing",
        "I reduced token costs by 38% with semantic caching before any client asked me to",
        "I work night shifts at a hotel while building AI systems during the day",
    ],
}


def profile_as_text() -> str:
    p = PROFILE
    skills_str = "\n".join(f"  {k}: {v}" for k, v in p["core_skills"].items())
    projects_str = "\n".join(
        f"  {proj['name']}: {proj['description']}"
        + (f" | Eval: {proj['eval_score']}" if "eval_score" in proj else "")
        for proj in p["projects"]
    )
    exp_str = "\n".join(
        f"  {e['role']} at {e['company']} ({e['period']}): {e['detail']}"
        for e in p["work_experience"]
    )
    langs_str = ", ".join(f"{lang} ({level})" for lang, level in p["languages"].items())
    return (
        f"Name: {p['name']}\n"
        f"Email: {p['email']} | Phone: {p['phone']}\n"
        f"Location: {p['location']} | GitHub: {p['github']}\n"
        f"University: {p['university']} — {p['degree']} ({p['semester']})\n"
        f"Availability: {p['availability']} | Role type: {p['role_type']}\n"
        f"Visa: {p['visa_status']}\n"
        f"Languages: {langs_str}\n"
        f"German filter: {p['german_filter']}\n\n"
        f"Target roles: {', '.join(p['target_roles'])}\n"
        f"Target companies: {p['target_companies']}\n\n"
        f"Core skills:\n{skills_str}\n\n"
        f"Projects:\n{projects_str}\n\n"
        f"Work experience:\n{exp_str}"
    )


class _Compat:
    """Attribute shim so cv_builder.py continues to work without changes."""
    name = PROFILE["name"]
    email = PROFILE["email"]
    phone = PROFILE["phone"]
    location = PROFILE["location"]
    github = PROFILE["github"]
    education = (
        f"{PROFILE['degree']}, {PROFILE['university']} ({PROFILE['semester']})"
    )
    languages = [
        f"{lang} ({level})" for lang, level in PROFILE["languages"].items()
    ]
    target_roles = PROFILE["target_roles"]
    salary_range = "€15–€20/hr (Werkstudent)"
    skills = list(PROFILE["core_skills"].keys())
    experience = [
        f"{e['role']} — {e['company']} ({e['period']}): {e['detail']}"
        for e in PROFILE["work_experience"]
    ]

    @staticmethod
    def as_text() -> str:
        return profile_as_text()


MY_PROFILE = _Compat()
