from __future__ import annotations

import io
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from abstraction.ports.report_generator_port import ReportGeneratorPort
from domain.entities.patient_report import PatientReport

_RISK_COLORS = {
    "high": colors.HexColor("#ef4444"),
    "moderate": colors.HexColor("#f59e0b"),
    "low": colors.HexColor("#22c55e"),
}
_HEADER_BG = colors.HexColor("#1e3a5f")
_LIGHT_ROW = colors.HexColor("#f1f5f9")


def _utcnow_label() -> str:
    return datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")


class ReportLabPdfGenerator(ReportGeneratorPort):
    """Generates a patient monitoring PDF report using ReportLab."""

    def generate(self, report: PatientReport) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        has_data = (
            report.risk_events
            or report.sensor_readings
            or report.medication_schedules
        )
        if has_data:
            story = (
                _build_header(report, styles)
                + _build_patient_summary(report, styles)
                + _build_risk_events(report, styles)
                + _build_sensor_summary(report, styles)
                + _build_medication_schedules(report, styles)
            )
        else:
            story = _build_no_data_page(report, styles)
        doc.build(story)
        return buf.getvalue()


# ── Section builders ─────────────────────────────────────────────────────────

def _build_no_data_page(report: PatientReport, styles) -> list:
    """Single-page fallback rendered when the patient has no data in the window."""
    title_style = ParagraphStyle(
        "no_data_title",
        parent=styles["Title"],
        fontSize=18,
        textColor=_HEADER_BG,
        spaceAfter=16,
    )
    body_style = ParagraphStyle(
        "no_data_body",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
        leading=18,
    )
    return [
        Spacer(1, 4 * cm),
        Paragraph("Rapport Médical — ChronicCare Nour", title_style),
        _divider(),
        Spacer(1, 1 * cm),
        Paragraph(
            "Aucune donnée disponible pour cette période.",
            ParagraphStyle(
                "no_data_main",
                parent=styles["Normal"],
                fontSize=16,
                textColor=colors.HexColor("#1e3a5f"),
                spaceAfter=12,
                leading=22,
            ),
        ),
        Paragraph(
            f"Patient : <b>{report.patient.display_name}</b>",
            body_style,
        ),
        Paragraph(
            f"Période analysée : <b>{report.days} derniers jours</b>",
            body_style,
        ),
        Paragraph(
            f"Rapport généré le {_utcnow_label()}",
            body_style,
        ),
    ]


def _h(text: str, styles, size: int = 13) -> Paragraph:
    style = ParagraphStyle(
        "section_title",
        parent=styles["Heading2"],
        fontSize=size,
        textColor=_HEADER_BG,
        spaceAfter=4,
    )
    return Paragraph(text, style)


def _body(text: str, styles) -> Paragraph:
    return Paragraph(text, styles["Normal"])


def _divider() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6)


def _build_header(report: PatientReport, styles) -> list:
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=20,
        textColor=_HEADER_BG,
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=12,
    )
    p = report.patient
    return [
        Paragraph("Rapport Médical — ChronicCare Nour", title_style),
        Paragraph(
            f"Patient : <b>{p.display_name}</b> &nbsp;|&nbsp; "
            f"Période : {report.days} derniers jours &nbsp;|&nbsp; "
            f"Généré le {_utcnow_label()}",
            sub_style,
        ),
        _divider(),
        Spacer(1, 0.3 * cm),
    ]


def _build_patient_summary(report: PatientReport, styles) -> list:
    p = report.patient
    data = [
        ["Âge", str(p.age), "Genre", p.gender],
        ["IMC", f"{p.bmi:.1f}", "HbA1c", f"{p.hba1c_last:.1f} %"],
        ["Glycémie de base", f"{p.baseline_glucose:.0f} mg/dL", "Email médecin", p.doctor_email],
        ["Comorbidités", ", ".join(p.comorbidities) or "—",
         "Médicaments", ", ".join(p.medications) or "—"],
    ]
    table = Table(data, colWidths=[4 * cm, 5 * cm, 4 * cm, 5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), _LIGHT_ROW),
        ("BACKGROUND", (2, 0), (2, -1), _LIGHT_ROW),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT_ROW]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [_h("Profil Patient", styles), table, Spacer(1, 0.5 * cm)]


def _build_risk_events(report: PatientReport, styles) -> list:
    events = report.risk_events
    counts = {"high": 0, "moderate": 0, "low": 0}
    for e in events:
        counts[e.risk_level] = counts.get(e.risk_level, 0) + 1

    summary = _body(
        f"Total : <b>{len(events)}</b> événements &nbsp;|&nbsp; "
        f"<font color='#ef4444'>Élevé : {counts['high']}</font> &nbsp;|&nbsp; "
        f"<font color='#f59e0b'>Modéré : {counts['moderate']}</font> &nbsp;|&nbsp; "
        f"<font color='#22c55e'>Faible : {counts['low']}</font>",
        styles,
    )

    if not events:
        return [_h("Événements de Risque", styles), summary, Spacer(1, 0.5 * cm)]

    header = [["Date", "Niveau", "Confiance", "Symptômes principaux"]]
    rows = []
    for e in events[:20]:  # cap at 20 rows to avoid overflow
        rows.append([
            e.timestamp.strftime("%d/%m %H:%M"),
            e.risk_level.upper(),
            f"{e.confidence:.0%}",
            ", ".join(e.extracted_symptoms[:3]) or "—",
        ])

    table = Table(header + rows, colWidths=[3 * cm, 3 * cm, 3 * cm, 9 * cm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_ROW]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, e in enumerate(events[:20], start=1):
        c = _RISK_COLORS.get(e.risk_level, colors.grey)
        style.append(("TEXTCOLOR", (1, i), (1, i), c))
        style.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))

    return [
        _h("Événements de Risque", styles), summary,
        Spacer(1, 0.2 * cm), table, Spacer(1, 0.5 * cm),
    ]


def _build_sensor_summary(report: PatientReport, styles) -> list:
    readings = report.sensor_readings
    if not readings:
        return [
            _h("Lectures Capteurs", styles),
            _body("Aucune lecture disponible sur la période.", styles),
            Spacer(1, 0.5 * cm),
        ]

    latest = readings[0]
    avg_glucose = sum(r.glucose_mg_dl for r in readings) / len(readings)
    avg_hr = sum(r.heart_rate_bpm for r in readings) / len(readings)
    avg_spo2 = sum(r.spo2_pct for r in readings) / len(readings)

    data = [
        ["Métrique", "Dernière valeur", "Moyenne sur la période"],
        ["Glycémie (mg/dL)", f"{latest.glucose_mg_dl:.0f}", f"{avg_glucose:.0f}"],
        ["Fréquence cardiaque (bpm)", f"{latest.heart_rate_bpm}", f"{avg_hr:.0f}"],
        ["SpO₂ (%)", f"{latest.spo2_pct}", f"{avg_spo2:.0f}"],
        ["Pas aujourd'hui", f"{latest.steps_today}", "—"],
        ["Heures de sommeil", f"{latest.sleep_hours:.1f}", "—"],
    ]
    table = Table(data, colWidths=[7 * cm, 4.5 * cm, 6.5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_ROW]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    sub = _body(f"Basé sur <b>{len(readings)}</b> lecture(s) sur {report.days} jours.", styles)
    return [_h("Lectures Capteurs", styles), sub, Spacer(1, 0.2 * cm), table, Spacer(1, 0.5 * cm)]


def _build_medication_schedules(report: PatientReport, styles) -> list:
    schedules = report.medication_schedules
    if not schedules:
        return [
            _h("Rappels de Médicaments Actifs", styles),
            _body("Aucun rappel actif.", styles),
            Spacer(1, 0.5 * cm),
        ]

    header = [["Médicament", "Heure", "Fréquence", "Contexte repas"]]
    rows = [
        [s.medication, s.scheduled_time, s.frequency.replace("_", " "), s.meal_context]
        for s in schedules
    ]
    table = Table(header + rows, colWidths=[6 * cm, 3 * cm, 4 * cm, 5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_ROW]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [_h("Rappels de Médicaments Actifs", styles), table, Spacer(1, 0.5 * cm)]
