"""PDF rendering for a lecture's study pack.

Uses reportlab — pure-Python, no native deps, no paid API.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.lecture import LectureDB


# Brand colors mirroring the web UI
BRAND_PRIMARY = colors.HexColor("#001F4D")   # Oxford Blue
BRAND_ACCENT = colors.HexColor("#CCFF00")   # Highlighter yellow-green
BRAND_MUTED = colors.HexColor("#666666")
BRAND_BORDER = colors.HexColor("#E5E5E5")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Overline": ParagraphStyle(
            "Overline",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=BRAND_PRIMARY,
            spaceAfter=4,
            letterSpacing=2,
        ),
        "Title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=BRAND_PRIMARY,
            spaceAfter=8,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=11,
            textColor=BRAND_MUTED,
            spaceAfter=18,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=BRAND_PRIMARY,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=10.5,
            leading=14,
            leftIndent=18,
            bulletIndent=4,
            spaceAfter=4,
        ),
        "Concept": ParagraphStyle(
            "Concept",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=BRAND_PRIMARY,
        ),
        "QuestionNum": ParagraphStyle(
            "QuestionNum",
            parent=base["Normal"],
            fontSize=8,
            textColor=BRAND_MUTED,
        ),
        "Question": ParagraphStyle(
            "Question",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            spaceAfter=4,
        ),
        "Option": ParagraphStyle(
            "Option",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=14,
        ),
        "Answer": ParagraphStyle(
            "Answer",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=13,
            textColor=BRAND_PRIMARY,
            leftIndent=14,
            spaceAfter=10,
        ),
        "Footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=8,
            textColor=BRAND_MUTED,
            alignment=1,
        ),
    }


def render_lecture_pdf(lecture: LectureDB) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title=f"LectureMind — {lecture.title}",
        author="LectureMind AI",
    )
    s = _styles()
    materials = lecture.materials
    elements: list = []

    # Brand header
    overline_cells = [
        [Paragraph("LECTUREMIND  ·  STUDY PACK", s["Overline"])],
    ]
    header_tbl = Table(overline_cells, colWidths=[doc.width])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_tbl)
    elements.append(Spacer(1, 18))

    # Title block
    elements.append(Paragraph(_escape(lecture.title), s["Title"]))
    subtitle_bits = [b for b in (lecture.subject, lecture.semester) if b]
    if subtitle_bits:
        elements.append(Paragraph(" · ".join(_escape(b) for b in subtitle_bits), s["Subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=14))

    # Summary
    if materials.summary:
        elements.append(Paragraph("TL;DR", s["Overline"]))
        elements.append(Paragraph(_escape(materials.summary), s["Body"]))
        elements.append(Spacer(1, 10))

    # Smart notes
    if materials.smart_notes:
        elements.append(Paragraph("Smart Notes", s["H2"]))
        for i, note in enumerate(materials.smart_notes, 1):
            elements.append(Paragraph(
                f"<font color='#001F4D'><b>{i:02d}</b></font>&nbsp;&nbsp;{_escape(note)}",
                s["Body"],
            ))

    # Key concepts
    if materials.key_concepts:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Key Concepts", s["H2"]))
        concept_text = "  ·  ".join(_escape(c) for c in materials.key_concepts)
        elements.append(Paragraph(concept_text, s["Concept"]))

    # Quiz (with answer key inline)
    if materials.quiz:
        elements.append(PageBreak())
        elements.append(Paragraph("Quiz", s["H2"]))
        elements.append(Paragraph(
            "Answers and explanations are revealed below each question.",
            s["Subtitle"],
        ))
        for i, q in enumerate(materials.quiz, 1):
            elements.append(Paragraph(f"Question {i:02d}", s["Overline"]))
            elements.append(Paragraph(_escape(q.question), s["Question"]))
            for oi, opt in enumerate(q.options):
                letter = chr(65 + oi)
                marker = "■" if oi == q.answer_index else "□"
                elements.append(Paragraph(
                    f"{marker} <b>{letter}.</b> {_escape(opt)}",
                    s["Option"],
                ))
            if q.explanation:
                elements.append(Paragraph(
                    f"<b>Answer:</b> {chr(65 + q.answer_index)} — {_escape(q.explanation)}",
                    s["Answer"],
                ))
            else:
                elements.append(Paragraph(
                    f"<b>Answer:</b> {chr(65 + q.answer_index)}",
                    s["Answer"],
                ))

    # Flashcards
    if materials.flashcards:
        elements.append(PageBreak())
        elements.append(Paragraph("Flashcards", s["H2"]))
        rows = [[
            Paragraph("<b>Front</b>", s["Concept"]),
            Paragraph("<b>Back</b>", s["Concept"]),
        ]]
        for c in materials.flashcards:
            rows.append([
                Paragraph(_escape(c.front), s["Body"]),
                Paragraph(_escape(c.back), s["Body"]),
            ])
        col_w = doc.width / 2
        flash_tbl = Table(rows, colWidths=[col_w, col_w], repeatRows=1)
        flash_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_ACCENT),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(flash_tbl)

    def _draw_footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(BRAND_MUTED)
        canvas.drawString(0.85 * inch, 0.5 * inch, "Generated by LectureMind AI")
        canvas.drawRightString(
            doc.pagesize[0] - 0.85 * inch,
            0.5 * inch,
            f"Page {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buf.getvalue()


def _escape(s: str) -> str:
    """Escape HTML entities for reportlab Paragraph."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
