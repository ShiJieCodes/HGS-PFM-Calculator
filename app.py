
import streamlit as st
import sqlite3
from datetime import datetime
import os
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether
)

# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="HGS PFM Calculator",
    page_icon="💪",
    layout="wide"
)


# =========================================================
# REFERENCE DATA
# =========================================================
#
# median_hgs = median HGS reference for age/sex
# avg_lm     = population average Lean Mass
# avg_bw     = population average Body Weight
#
# avg_lm / avg_bw are None where the current reference table
# does not provide body-composition values.
# =========================================================

MALE_REFERENCE = {
    "20-24": {"median_hgs": 40.0, "avg_lm": 51.2, "avg_bw": 80.4},
    "25-29": {"median_hgs": 41.0, "avg_lm": 51.2, "avg_bw": 80.4},
    "30-34": {"median_hgs": 42.0, "avg_lm": 52.1, "avg_bw": 81.2},
    "35-39": {"median_hgs": 42.0, "avg_lm": 52.1, "avg_bw": 81.2},
    "40-44": {"median_hgs": 41.0, "avg_lm": 49.0, "avg_bw": 76.8},
    "45-49": {"median_hgs": 36.0, "avg_lm": 49.0, "avg_bw": 76.8},
    "50-54": {"median_hgs": 34.5, "avg_lm": 49.3, "avg_bw": 73.5},
    "55-59": {"median_hgs": 33.5, "avg_lm": 49.3, "avg_bw": 73.5},
    "60-64": {"median_hgs": 31.0, "avg_lm": 43.4, "avg_bw": 66.2},
    "65-69": {"median_hgs": 29.0, "avg_lm": 42.2, "avg_bw": 65.9},
    "70-74": {"median_hgs": 27.5, "avg_lm": 41.3, "avg_bw": 65.4},
    "75-79": {"median_hgs": 26.0, "avg_lm": 40.0, "avg_bw": 63.0},
    "80-84": {"median_hgs": 24.0, "avg_lm": 38.9, "avg_bw": 61.6},

    # HGS reference exists, but LM/BW population reference
    # is not currently available from your table.
    "85-89": {"median_hgs": 21.0, "avg_lm": None, "avg_bw": None},
    "90-94": {"median_hgs": 18.5, "avg_lm": None, "avg_bw": None},
    "95-99": {"median_hgs": 18.0, "avg_lm": None, "avg_bw": None},
    "100+": {"median_hgs": 15.8, "avg_lm": None, "avg_bw": None},
}


FEMALE_REFERENCE = {
    "20-24": {"median_hgs": 25.0, "avg_lm": 32.9, "avg_bw": 57.7},
    "25-29": {"median_hgs": 25.0, "avg_lm": 32.9, "avg_bw": 57.7},
    "30-34": {"median_hgs": 25.0, "avg_lm": 34.9, "avg_bw": 61.3},
    "35-39": {"median_hgs": 25.0, "avg_lm": 34.9, "avg_bw": 61.3},
    "40-44": {"median_hgs": 24.0, "avg_lm": 35.4, "avg_bw": 63.4},
    "45-49": {"median_hgs": 23.5, "avg_lm": 35.4, "avg_bw": 63.4},
    "50-54": {"median_hgs": 22.0, "avg_lm": 35.1, "avg_bw": 63.0},
    "55-59": {"median_hgs": 21.5, "avg_lm": 35.1, "avg_bw": 63.0},
    "60-64": {"median_hgs": 20.0, "avg_lm": 32.1, "avg_bw": 58.8},
    "65-69": {"median_hgs": 19.0, "avg_lm": 32.2, "avg_bw": 59.3},

    # Spreadsheet labels were overlapping (>70, 75-80, >80).
    # These are cleaned into non-overlapping bands.
    "70-74": {"median_hgs": 18.0, "avg_lm": 29.9, "avg_bw": 53.8},
    "75-79": {"median_hgs": 16.8, "avg_lm": 31.0, "avg_bw": 57.5},
    "80-84": {"median_hgs": 15.0, "avg_lm": 28.7, "avg_bw": 52.8},

    "85-89": {"median_hgs": 14.0, "avg_lm": None, "avg_bw": None},
    "90-94": {"median_hgs": 12.0, "avg_lm": None, "avg_bw": None},
    "95-99": {"median_hgs": 11.0, "avg_lm": None, "avg_bw": None},
    "100+": {"median_hgs": 10.0, "avg_lm": None, "avg_bw": None},
}


# =========================================================
# AGE GROUP MAPPING
# =========================================================

def get_age_group(age):
    if 20 <= age <= 24:
        return "20-24"
    elif 25 <= age <= 29:
        return "25-29"
    elif 30 <= age <= 34:
        return "30-34"
    elif 35 <= age <= 39:
        return "35-39"
    elif 40 <= age <= 44:
        return "40-44"
    elif 45 <= age <= 49:
        return "45-49"
    elif 50 <= age <= 54:
        return "50-54"
    elif 55 <= age <= 59:
        return "55-59"
    elif 60 <= age <= 64:
        return "60-64"
    elif 65 <= age <= 69:
        return "65-69"
    elif 70 <= age <= 74:
        return "70-74"
    elif 75 <= age <= 79:
        return "75-79"
    elif 80 <= age <= 84:
        return "80-84"
    elif 85 <= age <= 89:
        return "85-89"
    elif 90 <= age <= 94:
        return "90-94"
    elif 95 <= age <= 99:
        return "95-99"
    elif age >= 100:
        return "100+"

    return None

# =========================================================
# PDF REPORT GENERATOR
# =========================================================

def generate_pdf_report(result, summary):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    story = []

    # =====================================================
    # BRAND COLOURS
    # =====================================================

    DARK_BLUE = colors.HexColor("#005F86")
    BLUE = colors.HexColor("#00A6D6")
    LIGHT_BLUE = colors.HexColor("#EAF7FB")

    GREEN = colors.HexColor("#88C540")
    LIGHT_GREEN = colors.HexColor("#F0F8E9")

    ORANGE = colors.HexColor("#F0A36B")
    LIGHT_ORANGE = colors.HexColor("#FFF3EB")

    DARK_TEXT = colors.HexColor("#263238")
    GREY_TEXT = colors.HexColor("#607D8B")
    LIGHT_GREY = colors.HexColor("#F5F7F8")
    BORDER = colors.HexColor("#DDE5E8")

    WHITE = colors.white

    # =====================================================
    # TEXT STYLES
    # =====================================================

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=DARK_BLUE,
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=GREY_TEXT,
    )

    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=DARK_BLUE,
        spaceBefore=7,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=GREY_TEXT,
    )

    centre_small = ParagraphStyle(
        "CentreSmall",
        parent=small_style,
        alignment=TA_CENTER,
    )

    score_label_style = ParagraphStyle(
        "ScoreLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=GREY_TEXT,
    )

    score_value_style = ParagraphStyle(
        "ScoreValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=28,
        alignment=TA_CENTER,
        textColor=DARK_BLUE,
    )

    score_status_style = ParagraphStyle(
        "ScoreStatus",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=DARK_TEXT,
    )

    # =====================================================
    # HEADER
    # =====================================================

    logo_path = "etern_medical_logo.png"

    if os.path.exists(logo_path):
        logo = Image(
            logo_path,
            width=55 * mm,
            height=18 * mm
        )
    else:
        logo = Paragraph(
            "<b>ETERN MEDICAL</b>",
            title_style
        )

    header_text = [
        Paragraph(
            "Hand Grip Strength",
            title_style
        ),
        Paragraph(
            "PFM Assessment Report",
            subtitle_style
        )
    ]

    header = Table(
        [
            [
                logo,
                header_text
            ]
        ],
        colWidths=[
            70 * mm,
            105 * mm
        ]
    )

    header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    story.append(header)

    story.append(Spacer(1, 4 * mm))

    # Small brand line
    brand_line = Table(
        [[""]],
        colWidths=[178 * mm],
        rowHeights=[1.5 * mm]
    )

    brand_line.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLUE)
        ])
    )

    story.append(brand_line)

    story.append(Spacer(1, 5 * mm))

    # =====================================================
    # PATIENT DETAILS
    # =====================================================

    story.append(
        Paragraph(
            "Patient Information",
            section_title
        )
    )

    report_date = datetime.now().strftime("%d %B %Y")

    patient_details = [
        [
            Paragraph("<b>Patient</b>", small_style),
            Paragraph(result["patient_name"], normal_style),

            Paragraph("<b>Patient ID</b>", small_style),
            Paragraph(
                result["patient_id"] if result["patient_id"] else "-",
                normal_style
            ),
        ],
        [
            Paragraph("<b>Age</b>", small_style),
            Paragraph(
                f'{result["age"]} years',
                normal_style
            ),

            Paragraph("<b>Sex</b>", small_style),
            Paragraph(
                result["sex"],
                normal_style
            ),
        ],
        [
            Paragraph("<b>Reference Group</b>", small_style),
            Paragraph(
                f'{result["sex"]}, {result["age_group"]}',
                normal_style
            ),

            Paragraph("<b>Assessment Date</b>", small_style),
            Paragraph(
                report_date,
                normal_style
            ),
        ],
    ]

    patient_table = Table(
        patient_details,
        colWidths=[
            30 * mm,
            60 * mm,
            30 * mm,
            58 * mm
        ]
    )

    patient_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),

            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(patient_table)

    story.append(Spacer(1, 6 * mm))

    # =====================================================
    # SCORE CARDS
    # =====================================================

    story.append(
        Paragraph(
            "Your PFM Profile",
            section_title
        )
    )

    performance_status = score_category(
        result["performance"]
    )

    metabolic_status = (
        score_category(result["metabolic"])
        if result["metabolic"] is not None
        else "Not available"
    )

    functionality_status = (
        score_category(result["functionality"])
        if result["functionality"] is not None
        else "Not available"
    )

    metabolic_value = (
        f'{result["metabolic"]:.0f}%'
        if result["metabolic"] is not None
        else "N/A"
    )

    functionality_value = (
        f'{result["functionality"]:.0f}%'
        if result["functionality"] is not None
        else "N/A"
    )

    performance_card = [
        Paragraph(
            "P - PERFORMANCE",
            score_label_style
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            f'{result["performance"]:.0f}%',
            score_value_style
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            performance_status,
            score_status_style
        ),
    ]

    metabolic_card = [
        Paragraph(
            "M - METABOLIC",
            score_label_style
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            metabolic_value,
            score_value_style
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            metabolic_status,
            score_status_style
        ),
    ]

    functionality_card = [
        Paragraph(
            "F - FUNCTIONALITY",
            score_label_style
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            functionality_value,
            score_value_style
        ),
        Spacer(1, 1 * mm),
        Paragraph(
            functionality_status,
            score_status_style
        ),
    ]

    scores_table = Table(
        [[
            performance_card,
            metabolic_card,
            functionality_card
        ]],
        colWidths=[
            58 * mm,
            58 * mm,
            58 * mm
        ],
        rowHeights=[37 * mm]
    )

    scores_table.setStyle(
        TableStyle([

            ("BACKGROUND", (0, 0), (0, 0), LIGHT_BLUE),
            ("BACKGROUND", (1, 0), (1, 0), LIGHT_ORANGE),
            ("BACKGROUND", (2, 0), (2, 0), LIGHT_GREEN),

            ("BOX", (0, 0), (0, 0), 1, BLUE),
            ("BOX", (1, 0), (1, 0), 1, ORANGE),
            ("BOX", (2, 0), (2, 0), 1, GREEN),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),

            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )

    story.append(scores_table)

    story.append(Spacer(1, 6 * mm))

    # =====================================================
    # SUMMARY / INTERPRETATION
    # =====================================================

    story.append(
        Paragraph(
            "Overall Interpretation",
            section_title
        )
    )

    summary_box = Table(
        [[Paragraph(summary, normal_style)]],
        colWidths=[178 * mm]
    )

    summary_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFB")),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ])
    )

    story.append(summary_box)

    story.append(Spacer(1, 5 * mm))

    # =====================================================
    # MEASUREMENTS
    # =====================================================

    story.append(
        Paragraph(
            "Assessment Measurements",
            section_title
        )
    )

    measurement_data = [
        [
            Paragraph(
                "HAND GRIP STRENGTH",
                centre_small
            ),
            Paragraph(
                "LEAN MASS",
                centre_small
            ),
            Paragraph(
                "BODY WEIGHT",
                centre_small
            ),
        ],
        [
            Paragraph(
                f'<b>{result["hgs"]:.1f} kg</b>',
                ParagraphStyle(
                    "Measure1",
                    parent=normal_style,
                    alignment=TA_CENTER,
                    fontSize=14,
                    leading=16,
                    textColor=DARK_BLUE
                )
            ),

            Paragraph(
                f'<b>{result["lean_mass"]:.1f} kg</b>',
                ParagraphStyle(
                    "Measure2",
                    parent=normal_style,
                    alignment=TA_CENTER,
                    fontSize=14,
                    leading=16,
                    textColor=DARK_BLUE
                )
            ),

            Paragraph(
                f'<b>{result["body_weight"]:.1f} kg</b>',
                ParagraphStyle(
                    "Measure3",
                    parent=normal_style,
                    alignment=TA_CENTER,
                    fontSize=14,
                    leading=16,
                    textColor=DARK_BLUE
                )
            ),
        ]
    ]

    measurement_table = Table(
        measurement_data,
        colWidths=[
            59.3 * mm,
            59.3 * mm,
            59.3 * mm
        ]
    )

    measurement_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(measurement_table)

    story.append(Spacer(1, 5 * mm))

    # =====================================================
    # WHAT EACH SCORE MEANS
    # =====================================================

    story.append(
        Paragraph(
            "Understanding Your Results",
            section_title
        )
    )

    interpretation_data = [
        [
            Paragraph(
                "<b>Performance</b>",
                normal_style
            ),
            Paragraph(
                "Compares your measured grip strength with the "
                "median grip strength of people of the same age "
                "and sex.",
                normal_style
            )
        ],

        [
            Paragraph(
                "<b>Metabolic</b>",
                normal_style
            ),
            Paragraph(
                "Compares grip strength relative to lean mass with "
                "the population reference. It reflects the amount "
                "of grip force produced relative to available lean "
                "mass.",
                normal_style
            )
        ],

        [
            Paragraph(
                "<b>Functionality</b>",
                normal_style
            ),
            Paragraph(
                "Compares grip strength relative to total body "
                "weight with the population reference.",
                normal_style
            )
        ],
    ]

    interpretation_table = Table(
        interpretation_data,
        colWidths=[
            34 * mm,
            144 * mm
        ]
    )

    interpretation_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),

            ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),

            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(interpretation_table)

    story.append(Spacer(1, 5 * mm))

    # =====================================================
    # REFERENCE VALUES
    # =====================================================

    story.append(
        Paragraph(
            "Reference Comparison",
            section_title
        )
    )

    ref_hgs_lm = (
        f'{result["reference_hgs_lm"]:.2f}'
        if result["reference_hgs_lm"] is not None
        else "N/A"
    )

    ref_hgs_bw = (
        f'{result["reference_hgs_bw"]:.2f}'
        if result["reference_hgs_bw"] is not None
        else "N/A"
    )

    reference_data = [
        [
            "Measure",
            "Patient",
            "Reference"
        ],
        [
            "Hand Grip Strength",
            f'{result["hgs"]:.1f} kg',
            f'{result["median_hgs"]:.1f} kg'
        ],
        [
            "HGS / Lean Mass",
            f'{result["patient_hgs_lm"]:.2f}',
            ref_hgs_lm
        ],
        [
            "HGS / Body Weight",
            f'{result["patient_hgs_bw"]:.2f}',
            ref_hgs_bw
        ],
    ]

    reference_table = Table(
        reference_data,
        colWidths=[
            75 * mm,
            51.5 * mm,
            51.5 * mm
        ]
    )

    reference_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),

            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

            ("BACKGROUND", (0, 1), (-1, -1), colors.white),

            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),

            ("ALIGN", (1, 0), (-1, -1), "CENTER"),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(reference_table)

    story.append(Spacer(1, 7 * mm))

    # =====================================================
    # CLINICAL NOTE
    # =====================================================

    clinical_note = Paragraph(
        "<b>Clinical note:</b> "
        "PFM results are reference-based comparisons intended to "
        "support clinical review and discussion. The Metabolic index "
        "represents grip strength relative to lean mass and does not "
        "directly measure metabolic rate, glucose metabolism, insulin "
        "resistance or other biochemical metabolic processes. Results "
        "should be interpreted together with clinical history, body "
        "composition and other relevant findings.",
        small_style
    )

    note_box = Table(
        [[clinical_note]],
        colWidths=[178 * mm]
    )

    note_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEF")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6D79F")),

            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(note_box)

    story.append(Spacer(1, 5 * mm))

    # =====================================================
    # FOOTER
    # =====================================================

    footer = Table(
        [[
            Paragraph(
                "Etern Medical",
                small_style
            ),
            Paragraph(
                "PFM Hand Grip Strength Assessment",
                centre_small
            ),
            Paragraph(
                report_date,
                ParagraphStyle(
                    "RightFooter",
                    parent=small_style,
                    alignment=2
                )
            )
        ]],
        colWidths=[
            50 * mm,
            78 * mm,
            50 * mm
        ]
    )

    footer.setStyle(
        TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, BORDER)
        ])
    )

    story.append(footer)

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(story)

    pdf = buffer.getvalue()

    buffer.close()

    return pdf
# =========================================================
# DATABASE
# =========================================================

def init_db():
    conn = sqlite3.connect("hgs_results.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hgs_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_name TEXT NOT NULL,
            patient_id TEXT,

            sex TEXT NOT NULL,
            age INTEGER NOT NULL,
            age_group TEXT NOT NULL,

            lean_mass REAL NOT NULL,
            body_weight REAL NOT NULL,
            hgs REAL NOT NULL,

            median_hgs REAL,

            patient_hgs_lm REAL,
            patient_hgs_bw REAL,

            reference_hgs_lm REAL,
            reference_hgs_bw REAL,

            performance REAL,
            metabolic REAL,
            functionality REAL,

            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_result(result):
    conn = sqlite3.connect("hgs_results.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO hgs_results (
            patient_name,
            patient_id,
            sex,
            age,
            age_group,
            lean_mass,
            body_weight,
            hgs,
            median_hgs,
            patient_hgs_lm,
            patient_hgs_bw,
            reference_hgs_lm,
            reference_hgs_bw,
            performance,
            metabolic,
            functionality,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["patient_name"],
        result["patient_id"],
        result["sex"],
        result["age"],
        result["age_group"],
        result["lean_mass"],
        result["body_weight"],
        result["hgs"],
        result["median_hgs"],
        result["patient_hgs_lm"],
        result["patient_hgs_bw"],
        result["reference_hgs_lm"],
        result["reference_hgs_bw"],
        result["performance"],
        result["metabolic"],
        result["functionality"],
        result["created_at"]
    ))

    conn.commit()
    conn.close()


def get_all_results():
    conn = sqlite3.connect("hgs_results.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM hgs_results
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# =========================================================
# PFM CALCULATOR
# =========================================================

def calculate_pfm(sex, age, lean_mass, body_weight, hgs):
    age_group = get_age_group(age)

    if age_group is None:
        return None

    if sex == "Male":
        reference = MALE_REFERENCE[age_group]
    else:
        reference = FEMALE_REFERENCE[age_group]

    median_hgs = reference["median_hgs"]
    avg_lm = reference["avg_lm"]
    avg_bw = reference["avg_bw"]

    # =====================================================
    # P = PERFORMANCE
    #
    # Patient HGS
    # ---------------- × 100
    # Median HGS
    # =====================================================

    performance = (hgs / median_hgs) * 100

    # =====================================================
    # PATIENT NORMALISED VALUES
    # =====================================================

    patient_hgs_lm = hgs / lean_mass
    patient_hgs_bw = hgs / body_weight

    reference_hgs_lm = None
    reference_hgs_bw = None

    metabolic = None
    functionality = None

    # =====================================================
    # M = METABOLIC
    #
    # Patient HGS / LM
    # -------------------------- × 100
    # Reference HGS / LM
    #
    # Reference HGS / LM:
    #
    # Median HGS ÷ Population Average LM
    # =====================================================

    if avg_lm is not None:
        reference_hgs_lm = median_hgs / avg_lm

        metabolic = (
            patient_hgs_lm
            / reference_hgs_lm
        ) * 100

    # =====================================================
    # F = FUNCTIONALITY
    #
    # Patient HGS / BW
    # -------------------------- × 100
    # Reference HGS / BW
    #
    # Reference HGS / BW:
    #
    # Median HGS ÷ Population Average BW
    # =====================================================

    if avg_bw is not None:
        reference_hgs_bw = median_hgs / avg_bw

        functionality = (
            patient_hgs_bw
            / reference_hgs_bw
        ) * 100

    return {
        "age_group": age_group,

        "median_hgs": median_hgs,
        "avg_lm": avg_lm,
        "avg_bw": avg_bw,

        "patient_hgs_lm": patient_hgs_lm,
        "patient_hgs_bw": patient_hgs_bw,

        "reference_hgs_lm": reference_hgs_lm,
        "reference_hgs_bw": reference_hgs_bw,

        "performance": performance,
        "metabolic": metabolic,
        "functionality": functionality,
    }


# =========================================================
# INTERPRETATION
# =========================================================
#
# These are prototype comparison bands.
#
# They are NOT diagnostic cut-offs.
#
# <80       Clearly below reference
# 80-89     Below reference
# 90-109    Around reference
# 110-119   Above reference
# >=120     Clearly above reference
# =========================================================

def score_category(score):
    if score is None:
        return "Not available"

    if score < 80:
        return "Clearly below reference"

    elif score < 90:
        return "Below reference"

    elif score < 110:
        return "Around reference"

    elif score < 120:
        return "Above reference"

    else:
        return "Clearly above reference"


# =========================================================
# INDIVIDUAL RESULT EXPLANATIONS
# =========================================================

def performance_explanation(score):
    if score >= 120:
        return (
            "Grip strength is clearly above the median reference "
            "for people of the same age and sex."
        )

    elif score >= 110:
        return (
            "Grip strength is above the median reference "
            "for people of the same age and sex."
        )

    elif score >= 90:
        return (
            "Grip strength is around the expected reference level "
            "for people of the same age and sex."
        )

    elif score >= 80:
        return (
            "Grip strength is below the median reference "
            "for people of the same age and sex."
        )

    else:
        return (
            "Grip strength is clearly below the median reference "
            "for people of the same age and sex."
        )


def metabolic_explanation(score):
    if score is None:
        return (
            "Metabolic comparison is not available because "
            "population lean-mass reference data are not available "
            "for this age group."
        )

    if score >= 120:
        return (
            "Grip strength relative to lean mass is clearly above "
            "the population reference."
        )

    elif score >= 110:
        return (
            "Grip strength relative to lean mass is above "
            "the population reference."
        )

    elif score >= 90:
        return (
            "Grip strength relative to lean mass is around "
            "the population reference."
        )

    elif score >= 80:
        return (
            "Grip strength relative to lean mass is below "
            "the population reference."
        )

    else:
        return (
            "Grip strength relative to lean mass is clearly below "
            "the population reference."
        )


def functionality_explanation(score):
    if score is None:
        return (
            "Functionality comparison is not available because "
            "population body-weight reference data are not available "
            "for this age group."
        )

    if score >= 120:
        return (
            "Grip strength relative to total body weight is clearly "
            "above the population reference."
        )

    elif score >= 110:
        return (
            "Grip strength relative to total body weight is above "
            "the population reference."
        )

    elif score >= 90:
        return (
            "Grip strength relative to total body weight is around "
            "the population reference."
        )

    elif score >= 80:
        return (
            "Grip strength relative to total body weight is below "
            "the population reference."
        )

    else:
        return (
            "Grip strength relative to total body weight is clearly "
            "below the population reference."
        )


# =========================================================
# COMBINED CLINICAL SUMMARY
# =========================================================

def generate_summary(performance, metabolic, functionality):
    statements = []

    # -----------------------------------------------------
    # PERFORMANCE
    # -----------------------------------------------------

    if performance >= 110:
        statements.append(
            "Absolute grip performance is above the age- and "
            "sex-specific reference."
        )

    elif performance < 90:
        statements.append(
            "Absolute grip performance is below the age- and "
            "sex-specific reference."
        )

    else:
        statements.append(
            "Absolute grip performance is around the age- and "
            "sex-specific reference."
        )

    # -----------------------------------------------------
    # IF METABOLIC / FUNCTIONALITY ARE NOT AVAILABLE
    # -----------------------------------------------------

    if metabolic is None or functionality is None:
        statements.append(
            "Metabolic and/or functionality comparison cannot be "
            "completed because the current reference table does not "
            "contain population lean-mass or body-weight values for "
            "this age group."
        )

        return " ".join(statements)

    # -----------------------------------------------------
    # COMBINED PATTERNS
    # -----------------------------------------------------

    if metabolic >= 110 and functionality < 90:
        statements.append(
            "Grip strength relative to lean mass is favourable, "
            "but strength relative to total body weight is lower. "
            "This means the patient produces good force relative "
            "to lean mass, while higher total body mass may reduce "
            "relative functional strength."
        )

    elif metabolic < 90 and functionality >= 110:
        statements.append(
            "Functional strength relative to total body weight is "
            "favourable, although grip strength relative to lean mass "
            "is below the population reference."
        )

    elif metabolic >= 110 and functionality >= 110:
        statements.append(
            "Both metabolic and functional strength indices are "
            "above the population reference."
        )

    elif metabolic < 90 and functionality < 90:
        statements.append(
            "Both metabolic and functional strength indices are "
            "below the population reference."
        )

    elif metabolic >= 110 and 90 <= functionality < 110:
        statements.append(
            "Metabolic strength is above reference while functional "
            "strength remains around the population reference."
        )

    elif functionality >= 110 and 90 <= metabolic < 110:
        statements.append(
            "Functional strength is above reference while metabolic "
            "strength remains around the population reference."
        )

    elif metabolic < 90 and 90 <= functionality < 110:
        statements.append(
            "Metabolic strength is below reference while functional "
            "strength remains around the population reference."
        )

    elif functionality < 90 and 90 <= metabolic < 110:
        statements.append(
            "Functional strength is below reference while metabolic "
            "strength remains around the population reference."
        )

    else:
        statements.append(
            "Metabolic and functional strength are generally around "
            "the population reference."
        )

    return " ".join(statements)


# =========================================================
# DATABASE INITIALISATION
# =========================================================

init_db()


# =========================================================
# APP HEADER
# =========================================================

st.title("💪 HGS PFM Calculator")

st.caption(
    "Performance • Metabolic • Functionality"
)

st.info(
    "Enter the patient's age, sex, Lean Mass, Body Weight and "
    "Hand Grip Strength. The calculator automatically selects "
    "the matching age- and sex-specific population reference."
)


# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3 = st.tabs([
    "🧮 New Assessment",
    "📋 Saved Results",
    "📖 How It Works"
])


# =========================================================
# TAB 1 — NEW ASSESSMENT
# =========================================================

with tab1:

    st.subheader("Patient Details")

    col1, col2 = st.columns(2)

    with col1:
        patient_name = st.text_input(
            "Patient Name"
        )

        patient_id = st.text_input(
            "Patient ID / Reference Number (optional)"
        )

    with col2:
        sex = st.selectbox(
            "Sex",
            ["Male", "Female"]
        )

        age = st.number_input(
            "Age",
            min_value=20,
            max_value=120,
            value=40,
            step=1
        )

    st.divider()

    st.subheader("Measurements")

    measurement1, measurement2, measurement3 = st.columns(3)

    with measurement1:
        lean_mass = st.number_input(
            "Lean Mass (kg)",
            min_value=1.0,
            max_value=150.0,
            value=40.0,
            step=0.1
        )

    with measurement2:
        body_weight = st.number_input(
            "Body Weight (kg)",
            min_value=1.0,
            max_value=300.0,
            value=60.0,
            step=0.1
        )

    with measurement3:
        hgs = st.number_input(
            "Hand Grip Strength (kg)",
            min_value=0.1,
            max_value=100.0,
            value=20.0,
            step=0.1
        )

    st.caption(
        "Lean Mass may be taken directly from the BCA. "
        "If required: Lean Mass = Body Weight × (1 − PBF / 100)."
    )

    calculate_button = st.button(
        "Calculate PFM",
        type="primary",
        use_container_width=True
    )

    if calculate_button:

        if not patient_name.strip():
            st.error(
                "Please enter the patient's name."
            )

        elif lean_mass > body_weight:
            st.error(
                "Lean Mass cannot normally be greater than total "
                "Body Weight. Please check the entered values."
            )

        else:
            result = calculate_pfm(
                sex,
                int(age),
                lean_mass,
                body_weight,
                hgs
            )

            if result is None:
                st.error(
                    "No reference data are available for this age."
                )

            else:
                st.session_state["current_result"] = {
                    "patient_name": patient_name.strip(),
                    "patient_id": patient_id.strip(),
                    "sex": sex,
                    "age": int(age),

                    "lean_mass": lean_mass,
                    "body_weight": body_weight,
                    "hgs": hgs,

                    **result
                }


    # =====================================================
    # DISPLAY CURRENT RESULT
    # =====================================================

    if "current_result" in st.session_state:

        result = st.session_state["current_result"]

        st.divider()

        st.subheader("PFM Results")

        st.write(
            f"**Reference group:** "
            f"{result['sex']}, age {result['age_group']}"
        )

        p_col, m_col, f_col = st.columns(3)

        # =================================================
        # P — PERFORMANCE
        # =================================================

        with p_col:

            st.metric(
                "P — Performance",
                f"{result['performance']:.0f}%"
            )

            st.caption(
                score_category(
                    result["performance"]
                )
            )

            st.write(
                performance_explanation(
                    result["performance"]
                )
            )

            st.write(
                f"Patient HGS: **{result['hgs']:.1f} kg**"
            )

            st.write(
                f"Reference Median HGS: "
                f"**{result['median_hgs']:.1f} kg**"
            )

        # =================================================
        # M — METABOLIC
        # =================================================

        with m_col:

            if result["metabolic"] is not None:

                st.metric(
                    "M — Metabolic",
                    f"{result['metabolic']:.0f}%"
                )

                st.caption(
                    score_category(
                        result["metabolic"]
                    )
                )

                st.write(
                    metabolic_explanation(
                        result["metabolic"]
                    )
                )

                st.write(
                    "Patient HGS / LM: "
                    f"**{result['patient_hgs_lm']:.2f}**"
                )

                st.write(
                    "Reference HGS / LM: "
                    f"**{result['reference_hgs_lm']:.2f}**"
                )

            else:

                st.metric(
                    "M — Metabolic",
                    "N/A"
                )

                st.caption(
                    "No population Lean Mass reference available"
                )

        # =================================================
        # F — FUNCTIONALITY
        # =================================================

        with f_col:

            if result["functionality"] is not None:

                st.metric(
                    "F — Functionality",
                    f"{result['functionality']:.0f}%"
                )

                st.caption(
                    score_category(
                        result["functionality"]
                    )
                )

                st.write(
                    functionality_explanation(
                        result["functionality"]
                    )
                )

                st.write(
                    "Patient HGS / BW: "
                    f"**{result['patient_hgs_bw']:.2f}**"
                )

                st.write(
                    "Reference HGS / BW: "
                    f"**{result['reference_hgs_bw']:.2f}**"
                )

            else:

                st.metric(
                    "F — Functionality",
                    "N/A"
                )

                st.caption(
                    "No population Body Weight reference available"
                )


        # =================================================
        # CLINICAL SUMMARY
        # =================================================

        st.subheader("Summary")

        summary = generate_summary(
            result["performance"],
            result["metabolic"],
            result["functionality"]
        )

        st.info(summary)

        # =========================================================
        # PDF REPORT
        # =========================================================

        pdf_data = generate_pdf_report(
            result,
            summary
        )

        safe_name = result["patient_name"].replace(" ", "_")

        pdf_filename = (
            f"HGS_PFM_{safe_name}_"
            f"{datetime.now().strftime('%Y%m%d')}.pdf"
        )

        st.download_button(
            label="📄 Download Patient PDF Report",
            data=pdf_data,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True
        )

        # =================================================
        # CALCULATION DETAILS
        # =================================================

        with st.expander("View Calculation Details"):

            st.write("### Patient Normalised Ratios")

            st.write(
                f"HGS / Lean Mass = "
                f"{result['hgs']:.1f} ÷ "
                f"{result['lean_mass']:.1f} "
                f"= **{result['patient_hgs_lm']:.3f}**"
            )

            st.write(
                f"HGS / Body Weight = "
                f"{result['hgs']:.1f} ÷ "
                f"{result['body_weight']:.1f} "
                f"= **{result['patient_hgs_bw']:.3f}**"
            )

            st.divider()

            st.write("### P — Performance")

            st.write(
                f"{result['hgs']:.1f} ÷ "
                f"{result['median_hgs']:.1f} × 100 "
                f"= **{result['performance']:.1f}%**"
            )

            if result["metabolic"] is not None:

                st.divider()

                st.write("### M — Metabolic")

                st.write(
                    "Reference HGS / LM = "
                    f"{result['median_hgs']:.1f} ÷ "
                    f"{result['avg_lm']:.1f} "
                    f"= **{result['reference_hgs_lm']:.3f}**"
                )

                st.write(
                    f"{result['patient_hgs_lm']:.3f} ÷ "
                    f"{result['reference_hgs_lm']:.3f} × 100 "
                    f"= **{result['metabolic']:.1f}%**"
                )

            if result["functionality"] is not None:

                st.divider()

                st.write("### F — Functionality")

                st.write(
                    "Reference HGS / BW = "
                    f"{result['median_hgs']:.1f} ÷ "
                    f"{result['avg_bw']:.1f} "
                    f"= **{result['reference_hgs_bw']:.3f}**"
                )

                st.write(
                    f"{result['patient_hgs_bw']:.3f} ÷ "
                    f"{result['reference_hgs_bw']:.3f} × 100 "
                    f"= **{result['functionality']:.1f}%**"
                )


        # =================================================
        # SAVE
        # =================================================

        if st.button(
            "💾 Save Assessment",
            use_container_width=True
        ):

            save_data = {
                **result,
                "created_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            save_result(save_data)

            st.success(
                "Assessment saved successfully."
            )


# =========================================================
# TAB 2 — SAVED RESULTS
# =========================================================

with tab2:

    st.subheader("Saved HGS Assessments")

    results = get_all_results()

    if len(results) == 0:

        st.info(
            "No assessments have been saved yet."
        )

    else:

        for row in results:

            with st.expander(
                f"{row['patient_name']} — "
                f"{row['sex']}, "
                f"{row['age']} years — "
                f"{row['created_at']}"
            ):

                if row["patient_id"]:
                    st.write(
                        f"Patient ID: **{row['patient_id']}**"
                    )

                st.write(
                    f"Reference group: "
                    f"**{row['sex']} {row['age_group']}**"
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Performance",
                        f"{row['performance']:.0f}%"
                    )

                with col2:
                    if row["metabolic"] is not None:
                        st.metric(
                            "Metabolic",
                            f"{row['metabolic']:.0f}%"
                        )
                    else:
                        st.metric(
                            "Metabolic",
                            "N/A"
                        )

                with col3:
                    if row["functionality"] is not None:
                        st.metric(
                            "Functionality",
                            f"{row['functionality']:.0f}%"
                        )
                    else:
                        st.metric(
                            "Functionality",
                            "N/A"
                        )

                st.write(
                    f"Lean Mass: **{row['lean_mass']:.1f} kg**"
                )

                st.write(
                    f"Body Weight: **{row['body_weight']:.1f} kg**"
                )

                st.write(
                    f"HGS: **{row['hgs']:.1f} kg**"
                )


# =========================================================
# TAB 3 — HOW IT WORKS
# =========================================================

with tab3:

    st.subheader("How the PFM Calculator Works")

    st.markdown("""
## P — Performance

This compares the patient's actual hand grip strength with
the median HGS for the same age and sex group.

**Formula**

`Performance % = Patient HGS ÷ Median HGS × 100`

Example:

Patient HGS = 18 kg
Median HGS = 16.8 kg

`18 ÷ 16.8 × 100 = 107%`

---

## M — Metabolic

The Metabolic component compares grip strength relative to
Lean Mass.

First calculate the patient's ratio:

`Patient HGS / LM = HGS ÷ Lean Mass`

Then calculate the population reference:

`Reference HGS / LM = Median HGS ÷ Population Average Lean Mass`

Then calculate:

`Metabolic % = Patient HGS/LM ÷ Reference HGS/LM × 100`

This should be interpreted as a comparison of grip strength
relative to lean mass.

It does not directly measure metabolic rate, insulin resistance,
glucose metabolism, mitochondrial function, or other biochemical
metabolic processes.

---

## F — Functionality

The Functionality component compares grip strength relative to
total Body Weight.

First calculate:

`Patient HGS / BW = HGS ÷ Body Weight`

Then calculate the population reference:

`Reference HGS / BW = Median HGS ÷ Population Average Body Weight`

Then:

`Functionality % = Patient HGS/BW ÷ Reference HGS/BW × 100`

This indicates how much grip strength the patient has relative
to their total body mass.

---

## Prototype Interpretation Bands

| Result | Interpretation |
|---|---|
| Below 80% | Clearly below reference |
| 80–89% | Below reference |
| 90–109% | Around reference |
| 110–119% | Above reference |
| 120% or above | Clearly above reference |

These bands are descriptive comparison bands for the prototype.

They should not be treated as validated diagnostic thresholds.

---

## Rounding

The calculator keeps the full decimal value internally.

For example:

`16.8 ÷ 31 = 0.541935...`

The calculation uses the complete value rather than rounding it
to 0.5 first.

This avoids unnecessary distortion of the final PFM percentage.

The app only rounds numbers when displaying them to the user.

---

## Required Inputs

The patient only needs:

- Sex
- Age
- Lean Mass
- Body Weight
- Hand Grip Strength

The rest of the values are calculated automatically from the
stored population reference tables.
""")


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "PFM HGS Calculator prototype. "
    "Reference-based comparison tool for clinical review."
)
