"""
PDF Generation Service.
Generates PDF reports in memory with internationalization (i18n) support
for labels in English and Portuguese.
"""
import io
import logging
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph

# --- Translation Dictionary (i18n) ---
translations = {
    "pt": {
        "generated_on": "Gerado em",
        "disclaimer": "Aviso: Apenas para fins informativos. Não é um conselho médico.",
        "title": "Seu Resumo de Saúde",
        "appointment": "Consulta",
        "age_bracket": "Faixa etária",
        "sex": "Sexo biológico",
        "chief_complaint": "Queixa Principal",
        "duration": "Duração",
        "complaint_detail": "Detalhes adicionais",
        "conditions": "Condições pré-existentes",
        "medications": "Medicamentos em uso",
        "allergies": "Alergias a medicamentos",
        "family_history": "Histórico familiar",
        "smoking": "Tabagismo",
        "alcohol": "Álcool",
        "qa_section_title": "Perguntas Clínicas e Respostas do Paciente",
        "question_label": "P",
        "answer_label": "R",
        "none_reported": "Não informado",
        "filename": "PreConsult_Resumo.pdf"
    },
    "en": {
        "generated_on": "Generated on",
        "disclaimer": "Disclaimer: For informational purposes only. Not medical advice.",
        "title": "Your Health Summary",
        "appointment": "Appointment",
        "age_bracket": "Age bracket",
        "sex": "Biological sex",
        "chief_complaint": "Chief Complaint",
        "duration": "Duration",
        "complaint_detail": "Additional details",
        "conditions": "Pre-existing conditions",
        "medications": "Current medications",
        "allergies": "Drug allergies",
        "family_history": "Family history",
        "smoking": "Smoking",
        "alcohol": "Alcohol",
        "qa_section_title": "Clinical Questions & Patient Answers",
        "question_label": "Q",
        "answer_label": "A",
        "none_reported": "None reported",
        "filename": "PreConsult_Report.pdf"
    }
}

def generate_pdf_report_in_memory(form: dict, qa_pairs: list, lang: str = 'en') -> tuple[bytes, str]:
    """
    Generates a PDF from a structured form and Q&A pairs, supporting multiple languages.

    Args:
        form (dict): The structured data from user input.
        qa_pairs (list): List of Q&A dictionaries or objects.
        lang (str): The language code ('pt' or 'en') for the report labels.

    Returns:
        tuple[bytes, str]: A tuple containing the PDF bytes and the recommended filename.
    """
    # Select the correct labels, defaulting to English if lang is invalid
    labels = translations.get(lang, translations['en'])
    none_reported_text = labels.get("none_reported", "None reported")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    styles = getSampleStyleSheet()

    # --- Header ---
    c.setFont("Helvetica", 9)
    c.drawRightString(width - inch, height - 0.9*inch, f"{labels['generated_on']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, height - 0.9*inch, labels['disclaimer'])

    # --- Title ---
    c.setFont("Helvetica-Bold", 18)
    c.drawString(inch, height - 1.2*inch, labels['title'])
    c.line(inch, height - 1.3*inch, width - inch, height - 1.3*inch)

    y_pos = height - 1.6*inch

    # --- Helper to draw a labeled section ---
    def draw_labeled_section(label, text, bold_label=True, padding=0.35 * inch):
        nonlocal c, y_pos
        style_body = styles['BodyText']
        style_body.fontName = 'Helvetica'
        style_body.fontSize = 12
        style_body.leading = 16

        full_text = f"<b>{label}:</b> {text}" if bold_label else f"{label}: {text}"
        p = Paragraph(full_text, style_body)

        p_width, p_height = p.wrapOn(c, width - 2 * inch, height)
        
        if y_pos - p_height < 1.0 * inch:
            c.showPage()
            y_pos = height - 1.0 * inch

        p.drawOn(c, inch, y_pos - p_height)

        y_pos = y_pos - p_height - padding

    def get_list_text(form_list):
        if not form_list:
            return none_reported_text
        if isinstance(form_list, list):
            return ", ".join(form_list) if form_list else none_reported_text
        return form_list

    # --- Patient Summary Section ---
    
    # Demographics & Appointment
    draw_labeled_section(labels['appointment'], form.get("specialist", none_reported_text), padding=0.2 * inch)
    draw_labeled_section(labels['age_bracket'], form.get("age_bracket", none_reported_text), padding=0.2 * inch)
    draw_labeled_section(labels['sex'], form.get("sex", none_reported_text))

    # Chief Complaint
    draw_labeled_section(labels['chief_complaint'], form.get("chief_complaint", none_reported_text), padding=0.2 * inch)
    draw_labeled_section(labels['duration'], form.get("duration", none_reported_text), padding=0.2 * inch)
    draw_labeled_section(labels['complaint_detail'], form.get("complaint_detail") or none_reported_text)

    # History
    draw_labeled_section(labels['conditions'], get_list_text(form.get("conditions")), padding=0.2 * inch)
    draw_labeled_section(labels['medications'], get_list_text(form.get("medications")), padding=0.2 * inch)
    draw_labeled_section(labels['allergies'], form.get("allergies") or none_reported_text, padding=0.2 * inch)
    draw_labeled_section(labels['family_history'], get_list_text(form.get("family_history")), padding=0.2 * inch)
    draw_labeled_section(labels['smoking'], form.get("smoking", none_reported_text), padding=0.2 * inch)
    draw_labeled_section(labels['alcohol'], form.get("alcohol", none_reported_text))

    # --- Clinical Questions & Patient Answers Section ---
    if qa_pairs:
        if y_pos < 2.0 * inch: c.showPage(); y_pos = height - 1.0 * inch
        else: y_pos -= 0.5 * inch
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(inch, y_pos, labels['qa_section_title'])
        c.line(inch, y_pos - 0.1*inch, width - inch, y_pos - 0.1*inch)
        y_pos -= 0.4 * inch

        for i, qa in enumerate(qa_pairs):
            q_text = qa.get("question", "") if isinstance(qa, dict) else getattr(qa, "question", "")
            a_text = qa.get("answer", "") if isinstance(qa, dict) else getattr(qa, "answer", "")
            
            draw_labeled_section(f"{labels['question_label']}{i+1}", q_text, bold_label=True, padding=0.15 * inch)
            draw_labeled_section(labels['answer_label'], a_text, bold_label=True)

    c.showPage()
    c.save()

    base_name = labels['filename'].replace('.pdf', '')
    timestamp = datetime.now().strftime('_%y%m%d%H%M')
    final_filename = f"{base_name}{timestamp}.pdf"

    pdf_bytes = buffer.getvalue()
    buffer.close()
    logging.info(f"PDF report generated in-memory (lang={lang}, size={len(pdf_bytes)} bytes).")
    return pdf_bytes, final_filename

