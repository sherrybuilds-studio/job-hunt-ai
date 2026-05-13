import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from profile import MY_PROFILE

ACCENT = colors.HexColor("#2d3a8c")
DARK = colors.HexColor("#1a1a2e")
GRAY = colors.HexColor("#555555")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "Name", parent=base["Title"],
            fontSize=22, textColor=DARK, spaceAfter=3, leading=26,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontSize=10, textColor=GRAY, spaceAfter=2, leading=14,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Normal"],
            fontSize=11, textColor=ACCENT, spaceBefore=10, spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=10, textColor=DARK, leading=15, spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"],
            fontSize=10, textColor=DARK, leading=15, spaceAfter=3,
            leftIndent=12, firstLineIndent=-12,
        ),
    }


def build_cv(output_path: str = "sherry_cv.pdf") -> str:
    p = MY_PROFILE
    s = _styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    story = []

    # Header block
    story.append(Paragraph(p.name, s["name"]))
    story.append(Paragraph(
        f"{p.location} &nbsp;|&nbsp; {p.email} &nbsp;|&nbsp; {p.github}",
        s["subtitle"],
    ))
    story.append(Paragraph(
        f"Target: {', '.join(p.target_roles)} &nbsp;|&nbsp; Salary: {p.salary_range}",
        s["subtitle"],
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=6))

    # Education & languages
    story.append(Paragraph("Education", s["section"]))
    story.append(Paragraph(p.education, s["body"]))
    story.append(Paragraph(f"Languages: {', '.join(p.languages)}", s["body"]))

    # Skills
    story.append(Paragraph("Technical Skills", s["section"]))
    story.append(Paragraph(", ".join(p.skills), s["body"]))

    # Experience
    story.append(Paragraph("Experience", s["section"]))
    for exp in p.experience:
        story.append(Paragraph(f"• {exp}", s["bullet"]))

    doc.build(story)
    print(f"CV written to: {output_path}")
    return output_path


if __name__ == "__main__":
    build_cv()
