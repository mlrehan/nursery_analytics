"""Server-side branded PDF reports (ReportLab). Produces a consistent, enterprise
report for any dashboard module from the exact same computed data the UI shows."""
from __future__ import annotations

import datetime as dt
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

BRAND = colors.HexColor("#4f46e5")
BRAND_DK = colors.HexColor("#3730a3")
INK = colors.HexColor("#0b1220")
MUTED = colors.HexColor("#5b6678")
LINE = colors.HexColor("#d8deea")
ZEBRA = colors.HexColor("#f4f6fb")
PALETTE = [colors.HexColor(c) for c in
           ("#3b82f6", "#10b981", "#7c3aed", "#f59e0b", "#06b6d4", "#fb923c", "#ec4899", "#14b8a6")]

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm


def _fmt(value, unit) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if unit == "£":
        a = abs(v)
        if a >= 1_000_000:
            return f"{'-' if v < 0 else ''}£{a/1_000_000:.1f}M"
        if a >= 1_000:
            return f"{'-' if v < 0 else ''}£{a/1_000:.1f}K"
        return f"£{v:,.0f}"
    if unit == "%":
        return f"{v:g}%"
    return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold",
                             fontSize=18, textColor=INK, spaceAfter=2, leading=22),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, textColor=MUTED, leading=13),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=12,
                                   textColor=BRAND_DK, spaceBefore=10, spaceAfter=6, leading=15),
        "kpiLabel": ParagraphStyle("kpiLabel", fontName="Helvetica-Bold", fontSize=7.5,
                                   textColor=MUTED, leading=10),
        "kpiValue": ParagraphStyle("kpiValue", fontName="Helvetica-Bold", fontSize=17,
                                   textColor=INK, leading=20),
        "kpiSub": ParagraphStyle("kpiSub", fontName="Helvetica", fontSize=7, textColor=MUTED, leading=9),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, textColor=INK, leading=11),
        "cellR": ParagraphStyle("cellR", fontName="Helvetica", fontSize=8.5, textColor=INK,
                                leading=11, alignment=TA_RIGHT),
        "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, leading=11),
    }


# ─── chart drawings ───────────────────────────────────────────────────────────
def _bar_drawing(payload, width):
    cats = [str(c) for c in payload.get("categories", [])]
    series = payload.get("series", [])
    if not cats or not series:
        return None
    h = 150
    d = Drawing(width, h)
    bc = VerticalBarChart()
    bc.x, bc.y = 36, 34
    bc.width, bc.height = width - 60, h - 56
    bc.data = [[(0 if v is None else float(v)) for v in s.get("data", [])] for s in series]
    bc.categoryAxis.categoryNames = cats
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.angle = 20
    bc.categoryAxis.labels.boxAnchor = "ne"
    bc.valueAxis.labels.fontSize = 7
    bc.valueAxis.valueMin = 0
    bc.barSpacing = 1.5
    bc.groupSpacing = 8
    for i in range(len(bc.data)):
        bc.bars[i].fillColor = PALETTE[i % len(PALETTE)]
        bc.bars[i].strokeColor = None
    d.add(bc)
    if len(series) > 1:
        lg = Legend()
        lg.x, lg.y = 36, h - 6
        lg.fontSize = 7
        lg.alignment = "right"
        lg.columnMaximum = 1
        lg.dxTextSpace = 4
        lg.colorNamePairs = [(PALETTE[i % len(PALETTE)], s.get("name", "")) for i, s in enumerate(series)]
        lg.boxAnchor = "nw"
        d.add(lg)
    return d


def _pie_drawing(payload, width):
    data = payload.get("data", [])
    if not data:
        return None
    h = 150
    d = Drawing(width, h)
    pie = Pie()
    pie.x, pie.y = 20, 16
    pie.width = pie.height = h - 36
    pie.data = [max(0, float(x.get("value", 0))) for x in data]
    pie.labels = None
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    for i in range(len(pie.data)):
        pie.slices[i].fillColor = PALETTE[i % len(PALETTE)]
    d.add(pie)
    lg = Legend()
    lg.x, lg.y = h - 6, h - 18
    lg.fontSize = 8
    lg.dxTextSpace = 5
    lg.dy = 6
    lg.deltay = 12
    lg.colorNamePairs = [(PALETTE[i % len(PALETTE)], f"{x.get('name','')}  ({int(x.get('value',0))})")
                         for i, x in enumerate(data)]
    lg.boxAnchor = "nw"
    d.add(lg)
    return d


def _data_table(payload, viz, st, width):
    """Render a widget's data as a clean table (fallback / for table-ish widgets)."""
    header, rows = [], []
    if viz == "table":
        header = payload.get("columns", [])
        rows = payload.get("rows", [])
    elif viz in ("pie", "funnel"):
        header = ["Item", "Value"]
        rows = [[x.get("name", ""), x.get("value", 0)] for x in payload.get("data", [])]
    elif viz in ("bar", "stacked_bar"):
        cats = payload.get("categories", [])
        series = payload.get("series", [])
        header = ["Category"] + [s.get("name", "") for s in series]
        rows = [[c] + [s.get("data", [])[i] if i < len(s.get("data", [])) else "" for s in series]
                for i, c in enumerate(cats)]
    elif viz == "line":
        header = ["Series", "Latest", "Min", "Max", "Average"]
        for s in payload.get("series", []):
            vals = [float(v) for v in s.get("data", []) if v is not None]
            if vals:
                rows.append([s.get("name", ""), round(vals[-1], 1), round(min(vals), 1),
                             round(max(vals), 1), round(sum(vals) / len(vals), 1)])
    if not header or not rows:
        return None

    def numfmt(c):
        if isinstance(c, bool):
            return str(c)
        if isinstance(c, (int, float)):
            return f"{c:,.0f}" if float(c) == int(c) else f"{c:,.2f}"
        return str(c)

    head = [Paragraph(str(h), st["th"]) for h in header]
    body = []
    for r in rows:
        cells = [Paragraph(str(r[0]), st["cell"])]
        cells += [Paragraph(numfmt(c), st["cellR"]) for c in r[1:]]
        body.append(cells)
    ncol = len(header)
    first = width * 0.4
    rest = (width - first) / max(ncol - 1, 1)
    t = Table([head] + body, colWidths=[first] + [rest] * (ncol - 1), repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(body) + 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def _kpi_grid(kpis, st, width, per_row=3):
    """Grid of KPI tiles (label, big value, sub)."""
    tiles = []
    for w in kpis:
        p = w["payload"]
        label = p.get("label") or w["title"]
        val = _fmt(p.get("value"), p.get("unit", ""))
        if w["viz"] == "gauge":
            val = _fmt(p.get("value"), p.get("unit", "%"))
        inner = [[Paragraph(label.upper(), st["kpiLabel"])],
                 [Paragraph(val, st["kpiValue"])],
                 [Paragraph(p.get("sub", "") or "", st["kpiSub"])]]
        tt = Table(inner, colWidths=[(width / per_row) - 8])
        tt.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        tiles.append(tt)
    while len(tiles) % per_row:
        tiles.append("")
    grid = [tiles[i:i + per_row] for i in range(0, len(tiles), per_row)]
    t = Table(grid, colWidths=[width / per_row] * per_row)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
             ("LINEAFTER", (0, 0), (-2, -1), 0.4, LINE)]
    t.setStyle(TableStyle(style))
    return t


def build_report(*, brand_name, scope_label, module_name, widgets, data, generated_at=None):
    """widgets: [{key,title,viz}], data: {key: payload}. Returns PDF bytes."""
    generated_at = generated_at or dt.datetime.now()
    st = _styles()
    buf = io.BytesIO()
    avail = PAGE_W - 2 * MARGIN

    def on_page(canvas, doc):
        canvas.saveState()
        # header band
        canvas.setFillColor(BRAND)
        canvas.rect(0, PAGE_H - 14 * mm, PAGE_W, 14 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(MARGIN, PAGE_H - 9.4 * mm, brand_name)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 9.4 * mm, "Analytics Report")
        # footer
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(MARGIN, 8 * mm, f"Confidential · {brand_name}")
        canvas.drawCentredString(PAGE_W / 2, 8 * mm, generated_at.strftime("Generated %d %b %Y, %H:%M"))
        canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=20 * mm, bottomMargin=16 * mm, title=f"{module_name} — {brand_name}")
    frame = Frame(MARGIN, 16 * mm, avail, PAGE_H - 36 * mm, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])

    story = [Paragraph(module_name, st["h1"]), Paragraph(scope_label, st["sub"]), Spacer(1, 8)]

    kpis = [{"title": w["title"], "viz": w["viz"], "payload": data.get(w["key"], {})}
            for w in widgets if w["viz"] in ("kpi", "gauge") and data.get(w["key"])]
    if kpis:
        story.append(Paragraph("Key metrics", st["section"]))
        story.append(_kpi_grid(kpis, st, avail))

    for w in widgets:
        viz, payload = w["viz"], data.get(w["key"])
        if viz in ("kpi", "gauge") or not payload:
            continue
        flow = None
        try:
            if viz == "bar":
                flow = _bar_drawing(payload, avail)
            elif viz == "pie":
                flow = _pie_drawing(payload, avail)
        except Exception:
            flow = None
        if flow is None:
            flow = _data_table(payload, viz, st, avail)
        if flow is None:
            continue
        story.append(Paragraph(w["title"], st["section"]))
        story.append(flow)

    doc.build(story)
    return buf.getvalue()
