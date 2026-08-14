"""Generate a downloadable PDF report using ReportLab."""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


def _section(title, styles):
    return Paragraph(f"<b>{title}</b>", styles["H2"])


def build_pdf(result: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H2", fontSize=14, leading=18,
                              textColor=colors.HexColor("#1D4ED8"),
                              spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold"))
    body = styles["BodyText"]
    title = ParagraphStyle("T", parent=styles["Title"], textColor=colors.HexColor("#1D4ED8"))

    story = []
    parsed = result["parsed"]
    score = result["score"]

    story.append(Paragraph("AI Resume Screening &amp; Analysis Report", title))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"<b>Candidate:</b> {parsed.get('name','-')}", body))
    story.append(Paragraph(f"<b>Email:</b> {parsed.get('email','-')} &nbsp; "
                           f"<b>Phone:</b> {parsed.get('phone','-')}", body))
    if parsed.get("linkedin"): story.append(Paragraph(f"<b>LinkedIn:</b> {parsed['linkedin']}", body))
    if parsed.get("github"): story.append(Paragraph(f"<b>GitHub:</b> {parsed['github']}", body))

    # Scores table
    story.append(_section("Scores", styles))
    data = [
        ["Overall Resume Score", f"{score['overall']} / 100"],
        ["ATS Score", f"{score['ats']['score']} / 100"],
        ["Job Match %", f"{result['job_match_percent']}%"],
        ["Skill Match %", f"{score['skill_match']['percent']}%"],
        ["Completeness", f"{result['completeness']}%"],
    ]
    t = Table(data, colWidths=[8*cm, 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2563EB")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#CBD5E1")),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F4F8FF")]),
        ("PADDING",(0,0),(-1,-1),6),
    ]))
    story.append(t)

    # Breakdown
    story.append(_section("Score Breakdown", styles))
    bd = [["Component","Score"]] + [[k, f"{v}"] for k,v in score["breakdown"].items()]
    t2 = Table(bd, colWidths=[8*cm, 7*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1D4ED8")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#CBD5E1")),
        ("PADDING",(0,0),(-1,-1),6),
    ]))
    story.append(t2)

    # Skills
    story.append(_section("Matched Skills", styles))
    story.append(Paragraph(", ".join(score["skill_match"]["matched"]) or "—", body))
    story.append(_section("Missing Skills", styles))
    story.append(Paragraph(", ".join(score["skill_match"]["missing"]) or "—", body))

    # Strengths / Weaknesses / Suggestions
    for label, items in [
        ("Strengths", result["strengths"]),
        ("Weaknesses", result["weaknesses"]),
        ("Suggestions", result["suggestions"]),
    ]:
        story.append(_section(label, styles))
        if not items:
            story.append(Paragraph("—", body))
        else:
            for it in items:
                story.append(Paragraph(f"• {it}", body))

    # Career recommendations
    story.append(_section("Career Recommendations", styles))
    if result["careers"]:
        cr = [["Role","Match"]] + [[c["job_position"], f"{c['score']}%"] for c in result["careers"]]
        t3 = Table(cr, colWidths=[10*cm, 5*cm])
        t3.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#38BDF8")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#CBD5E1")),
            ("PADDING",(0,0),(-1,-1),6),
        ]))
        story.append(t3)

    doc.build(story)
    return buf.getvalue()
