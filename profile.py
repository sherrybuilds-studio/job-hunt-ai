from dataclasses import dataclass, field


@dataclass
class Profile:
    name: str = "Muhammad Shehryar (Sherry)"
    email: str = "sherrybuilds@gmail.com"
    location: str = "Berlin, Germany"
    github: str = "github.com/sherrybuilds-studio"
    education: str = "Computer Science Student, Berlin (self-taught practitioner first)"
    languages: list = field(default_factory=lambda: ["English", "Urdu", "German (learning)"])
    target_roles: list = field(default_factory=lambda: [
        "Werkstudent AI / Machine Learning",
        "Werkstudent Software Development",
        "Junior AI Developer",
        "Junior Automation Engineer",
        "AI Automation Developer part-time",
        "LLM Integration Developer part-time",
        "Junior Python Developer",
    ])
    location_filter: str = "Berlin, Germany"
    max_hours_per_week: int = 20
    salary_range: str = "€15–€20/hr (Werkstudent) or €35,000–€50,000 (Junior full-time)"
    skills: list = field(default_factory=lambda: [
        "Python", "FastAPI", "ChromaDB", "n8n", "RAG",
        "Semantic Caching", "WhatsApp Bots", "VPS Deployment",
        "PM2", "Supabase", "OpenClaw", "Anthropic SDK", "OpenRouter",
    ])
    portfolio: list = field(default_factory=lambda: [
        (
            "Montari Oak AI Sales System (production) — built solo for a luxury interior design brand. "
            "Full stack: web scraping → ChromaDB vector store → RAG pipeline with semantic caching → "
            "FastAPI backend → WhatsApp bot → Supabase. Running 24/7 with real customers. "
            "Every layer designed, deployed, and debugged by me"
        ),
        (
            "CV Job Hunter (this tool) — autonomous daily agent that scrapes Adzuna for AI jobs in Berlin, "
            "scores each with Claude via OpenRouter, generates a tailored cover letter per match, "
            "saves to Supabase, and sends a Telegram digest. Built in one session, fully operational"
        ),
        (
            "n8n Automation Workflows — multi-step business automations with webhook triggers, "
            "API chaining, conditional branching, and external service integrations. "
            "Deployed on VPS with PM2, running unattended"
        ),
    ])
    experience: list = field(default_factory=lambda: [
        (
            "Self-taught AI developer — learned by building production systems, not tutorials. "
            "Studied CS while working nightshifts; every skill came from debugging real failures "
            "and shipping things that actual users depend on"
        ),
        (
            "Comfortable across the full AI stack: data ingestion, vector DBs (ChromaDB), "
            "LLM integration (Anthropic SDK, OpenRouter), REST APIs (FastAPI), "
            "workflow automation (n8n), messaging (WhatsApp/Telegram bots), "
            "and cloud deployment (VPS, PM2, Supabase)"
        ),
    ])

    def as_text(self) -> str:
        skills_str = ", ".join(self.skills)
        portfolio_str = "\n".join(f"- {p}" for p in self.portfolio)
        exp_str = "\n".join(f"- {e}" for e in self.experience)
        roles_str = ", ".join(self.target_roles)
        langs_str = ", ".join(self.languages)
        return (
            f"Name: {self.name}\n"
            f"Email: {self.email}\n"
            f"Location: {self.location}\n"
            f"GitHub: {self.github}\n"
            f"Education: {self.education}\n"
            f"Languages: {langs_str}\n"
            f"Target roles: {roles_str}\n"
            f"Location constraint: {self.location_filter} only\n"
            f"Max hours/week: {self.max_hours_per_week} (werkstudent or part-time preferred)\n"
            f"Target salary: {self.salary_range}\n\n"
            f"Skills: {skills_str}\n\n"
            f"Portfolio projects:\n{portfolio_str}\n\n"
            f"Background:\n{exp_str}"
        )


MY_PROFILE = Profile()
