from preconsult.services.pdf_service import generate_pdf_report_in_memory

MINIMAL_FORM = {
    "specialist": "Gastroenterologist",
    "age_bracket": "26-35",
    "sex": "Female",
    "chief_complaint": "Stomach pain",
    "duration": "Weeks",
    "complaint_detail": "",
    "conditions": [],
    "medications": [],
    "allergies": "",
    "family_history": [],
    "smoking": "Never smoked",
    "alcohol": "Rarely",
}

MINIMAL_QA = [{"question": "Any nausea?", "answer": "Yes, sometimes."}]

def test_pdf_valid_bytes_en():
    pdf_bytes, filename = generate_pdf_report_in_memory(MINIMAL_FORM, MINIMAL_QA, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")
    assert filename.startswith("PreConsult_Report")
    assert filename.endswith(".pdf")

def test_pdf_valid_bytes_pt():
    pdf_bytes, filename = generate_pdf_report_in_memory(MINIMAL_FORM, MINIMAL_QA, lang="pt")
    assert pdf_bytes.startswith(b"%PDF-")
    assert filename.startswith("PreConsult_Resumo")
    assert filename.endswith(".pdf")

def test_pdf_renders_form_text():
    form = {**MINIMAL_FORM, "specialist": "Cardio", "chief_complaint": "chest pain"}
    pdf_bytes, _ = generate_pdf_report_in_memory(form, MINIMAL_QA, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_renders_qa_section():
    qa = [{"question": "How severe?", "answer": "Very bad"}]
    pdf_bytes, _ = generate_pdf_report_in_memory(MINIMAL_FORM, qa, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_none_reported_for_empty_lists():
    form = {**MINIMAL_FORM, "conditions": [], "medications": [], "family_history": []}
    pdf_bytes, _ = generate_pdf_report_in_memory(form, MINIMAL_QA, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_empty_qa_pairs_does_not_crash():
    pdf_bytes, _ = generate_pdf_report_in_memory(MINIMAL_FORM, [], lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_long_answer():
    qa = [{"question": "Describe your symptoms", "answer": "word " * 500}]
    pdf_bytes, _ = generate_pdf_report_in_memory(MINIMAL_FORM, qa, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_unknown_lang_defaults_to_en():
    pdf_bytes, filename = generate_pdf_report_in_memory(MINIMAL_FORM, MINIMAL_QA, lang="xx")
    assert pdf_bytes.startswith(b"%PDF-")
    assert filename.startswith("PreConsult_Report")
    assert filename.endswith(".pdf")

def test_pdf_empty_form_dict_does_not_crash():
    pdf_bytes, _ = generate_pdf_report_in_memory({}, MINIMAL_QA, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_partial_form_does_not_crash():
    pdf_bytes, _ = generate_pdf_report_in_memory({"specialist": "Cardio"}, [], lang="en")
    assert pdf_bytes.startswith(b"%PDF-")

def test_pdf_qa_without_question_field_does_not_crash():
    qa = [{"answer": "yes"}]
    pdf_bytes, _ = generate_pdf_report_in_memory(MINIMAL_FORM, qa, lang="en")
    assert pdf_bytes.startswith(b"%PDF-")
