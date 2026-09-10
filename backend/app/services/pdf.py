from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas


def create_minutes_pdf(title: str, summary: dict[str, Any]) -> bytes:
    stream = BytesIO()
    y = 800
    canvas = Canvas(stream, pagesize=A4)
    canvas.setTitle(title)

    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(50, y, title)
    y -= 35

    headings = (
        ("Agenda", summary.get("agenda", [])),
        ("Key decisions", summary.get("decisions", [])),
        ("Discussion points", summary.get("discussion", [])),
    )
    for heading, items in headings:
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(50, y, heading)
        y -= 20
        canvas.setFont("Helvetica", 10)
        for item in items:
            canvas.drawString(60, y, f"- {str(item)[:100]}")
            y -= 15
        y -= 10

    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(50, y, "Action items")
    y -= 20
    canvas.setFont("Helvetica", 10)
    for action in summary.get("actions", []):
        owner = action.get("owner", "Unassigned")
        task = action.get("task", "")
        due = action.get("due", "Not specified")
        line = f"- {owner}: {task} ({due})"[:110]
        canvas.drawString(60, y, line)
        y -= 15

    canvas.save()
    return stream.getvalue()
