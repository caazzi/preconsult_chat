"""Hand-written rubric and pricing cases for the offline benchmark harness.

Every scorer gets an explicit positive and negative case. The point is that the
rubric itself is testable independently of any provider, fixture or model call.
"""

import json
from pathlib import Path

import pytest

from scripts import bench_pricing, bench_scoring

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bench" / "complaints.json"


# ---------------------------------------------------------------------------
# Text normalization and count validity
# ---------------------------------------------------------------------------


def test_normalize_text_strips_accents_and_case():
    assert bench_scoring.normalize_text("  Você   está  BEM? ") == "voce esta bem?"


@pytest.mark.parametrize(
    ("questions", "expected"),
    [
        ([], False),
        (["one", "two"], False),
        (["one", "two", "three"], True),
        (["one", "two", "three", "four", "five"], True),
        (["one", "two", "three", "four", "five", "six"], False),
    ],
)
def test_count_validity_is_the_3_to_5_contract(questions, expected):
    assert bench_scoring.count_is_valid(questions) is expected


# ---------------------------------------------------------------------------
# Single-question heuristic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "When did the pain start?",
        "1. When did the pain start?",
        "- Does it spread anywhere?",
        "Quando a dor começou?",
        "When did the pain start",
    ],
)
def test_single_question_accepts_one_question(question):
    assert bench_scoring.is_single_question(question) is True


@pytest.mark.parametrize(
    "question",
    [
        "",
        "Tell me about the pain",
        "Is it sharp? Does it spread?",
        "Is it sharp. Does it spread?",
        "Two questions?\nSecond question?",
        "   ",
    ],
)
def test_single_question_rejects_compound_or_non_question_text(question):
    assert bench_scoring.is_single_question(question) is False


def test_single_question_ratio_positive_and_negative():
    assert (
        bench_scoring.single_question_ratio(
            ["When did it start?", "What makes it worse?"]
        )
        == 1.0
    )
    assert (
        bench_scoring.single_question_ratio(
            ["When did it start?", "Is it sharp? Does it spread?"]
        )
        == 0.5
    )
    assert bench_scoring.single_question_ratio([]) == 0.0


# ---------------------------------------------------------------------------
# Language heuristics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("When did the pain start?", "en"),
        ("Does the feeling spread anywhere else?", "en"),
        ("Quando a dor começou?", "pt"),
        ("Como você está se sentindo?", "pt"),
        ("", "unknown"),
        ("12345", "unknown"),
    ],
)
def test_detect_language(text, expected):
    assert bench_scoring.detect_language(text) == expected


def test_language_match_ratio_and_threshold():
    english = ["When did it start?", "Does it spread?"]
    mixed = ["When did it start?", "Quando a dor começou?"]

    assert bench_scoring.language_match_ratio(english, "en") == 1.0
    assert bench_scoring.language_match_ratio(english, "pt") == 0.0
    assert bench_scoring.language_match_ratio(mixed, "en") == 0.5
    assert bench_scoring.language_match_ratio(mixed, "pt") == 0.5
    assert bench_scoring.language_match_ratio([], "en") == 0.0
    assert bench_scoring.language_matches(english, "en") is True
    assert bench_scoring.language_matches(mixed, "en") is False
    assert bench_scoring.language_matches(mixed, "en", threshold=0.5) is True


def test_language_match_rejects_unknown_language_code():
    with pytest.raises(ValueError, match="lang must be one of"):
        bench_scoring.language_match_ratio(["When did it start?"], "es")


# ---------------------------------------------------------------------------
# Banned diagnosis / treatment terms
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "You may have a migraine.",
        "It sounds like you have a virus.",
        "This suggests a muscle strain.",
        "Provavelmente você tem uma infecção.",
        "Parece que você tem uma alergia.",
    ],
)
def test_banned_diagnosis_phrases_are_found(question):
    assert bench_scoring.has_banned_terms([question]) is True


@pytest.mark.parametrize(
    "question",
    [
        "You should take ibuprofen 400 mg.",
        "Take this medication with food.",
        "I recommend starting antibiotics.",
        "Você deve tomar antibiótico.",
        "Tome este remédio duas vezes ao dia.",
    ],
)
def test_banned_treatment_phrases_are_found(question):
    assert bench_scoring.has_banned_terms([question]) is True


@pytest.mark.parametrize(
    "question",
    [
        "Have you been diagnosed with asthma?",
        "Are you currently taking any medications?",
        "Do you have any allergies?",
        "Have you had any treatment for this before?",
        "What dose of insulin do you take?",
        "Do you have a prescription for this medicine?",
        "Has a doctor prescribed anything for this?",
        "O médico já receitou algo para isso?",
        "Você já foi diagnosticado com asma?",
        "Você está tomando algum remédio?",
        "Qual a dose do seu remédio?",
    ],
)
def test_legitimate_history_questions_are_not_banned(question):
    assert bench_scoring.banned_terms_in([question]) == ()


def test_banned_terms_returns_the_matched_phrases():
    found = bench_scoring.banned_terms_in(["You should take ibuprofen."])

    assert "you should take" in found
    assert "take ibuprofen" in found


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------


def test_duplicate_ratio():
    assert bench_scoring.duplicate_ratio([]) == 0.0
    assert (
        bench_scoring.duplicate_ratio(["When did it start?", "Does it spread?"]) == 0.0
    )
    assert bench_scoring.duplicate_ratio(
        ["When did it start?", "when did it start", "Does it spread?"]
    ) == pytest.approx(1 / 3)
    assert bench_scoring.duplicate_ratio(["Same?", "Same?", "Same?"]) == pytest.approx(
        2 / 3
    )


# ---------------------------------------------------------------------------
# OPQRST / SAMPLE dimension coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "dimension"),
    [
        ("When did the pain start?", "onset"),
        ("What makes the pain worse?", "provocation"),
        ("What makes it better?", "palliation"),
        ("How would you describe the pain?", "quality"),
        ("Where do you feel the pain?", "region"),
        ("Does the pain spread to your arm?", "radiation"),
        ("On a scale from 1 to 10, how severe is it?", "severity"),
        ("How often does it happen?", "timing"),
        ("Have you noticed any other symptoms?", "associated"),
        ("Do you have any allergies?", "allergies"),
        ("Are you currently taking any medications?", "medications"),
        ("Have you had this problem before?", "past_history"),
        ("When did you last eat or drink?", "last_intake"),
        ("What happened right before it started?", "events"),
        ("Quando a dor começou?", "onset"),
        ("O que faz a dor piorar?", "provocation"),
        ("O que faz a dor melhorar?", "palliation"),
        ("Como você descreve a dor?", "quality"),
        ("Onde você sente a dor?", "region"),
        ("A dor se espalha para outro lugar?", "radiation"),
        ("Numa escala de 1 a 10, quão forte é?", "severity"),
        ("Com que frequência isso acontece?", "timing"),
        ("Você notou outros sintomas?", "associated"),
        ("Você tem alguma alergia?", "allergies"),
        ("Você está tomando algum remédio?", "medications"),
        ("Você já teve esse problema no passado?", "past_history"),
        ("Quando foi a última vez que você comeu?", "last_intake"),
        ("O que aconteceu antes de começar?", "events"),
    ],
)
def test_question_covers_each_dimension(question, dimension):
    assert bench_scoring.question_covers_dimension(question, dimension) is True


def test_question_does_not_cover_irrelevant_dimension():
    assert (
        bench_scoring.question_covers_dimension(
            "Do you have any allergies?", "radiation"
        )
        is False
    )


def test_unknown_dimension_raises_clearly():
    with pytest.raises(ValueError, match="unknown dimension"):
        bench_scoring.question_covers_dimension("When did it start?", "vibes")


def test_dimension_coverage_full_and_partial():
    questions = [
        "When did the pain start?",
        "On a scale from 1 to 10, how severe is it?",
    ]

    full = bench_scoring.dimension_coverage(questions, ["onset", "severity"])
    assert full.ratio == 1.0
    assert full.covered == ("onset", "severity")
    assert full.missing == ()

    partial = bench_scoring.dimension_coverage(
        questions, ["onset", "severity", "radiation"]
    )
    assert partial.ratio == pytest.approx(2 / 3)
    assert partial.covered == ("onset", "severity")
    assert partial.missing == ("radiation",)


def test_dimension_coverage_reports_observed_extra_axes():
    coverage = bench_scoring.dimension_coverage(
        ["Where do you feel the pain?"], ["onset"]
    )

    assert coverage.ratio == 0.0
    assert coverage.missing == ("onset",)
    assert "region" in coverage.observed


def test_dimension_coverage_empty_and_unknown_expected():
    empty = bench_scoring.dimension_coverage([], ["onset"])
    assert empty.ratio == 0.0
    assert empty.missing == ("onset",)

    no_expectations = bench_scoring.dimension_coverage([], [])
    assert no_expectations.ratio == 1.0

    with pytest.raises(ValueError, match="unknown expected dimension"):
        bench_scoring.dimension_coverage([], ["onset", "not_a_dimension"])


# ---------------------------------------------------------------------------
# Whole-list score
# ---------------------------------------------------------------------------


def test_score_questions_good_output():
    questions = [
        "When did the pressure start?",
        "What makes it worse?",
        "On a scale from 1 to 10, how severe is it?",
        "Does it spread anywhere else?",
    ]

    score = bench_scoring.score_questions(
        questions, "en", ["onset", "provocation", "severity", "radiation"]
    )

    assert score.question_count == 4
    assert score.count_valid is True
    assert score.single_question_ratio == 1.0
    assert score.language_match_ratio == 1.0
    assert score.language_matches is True
    assert score.banned_terms == ()
    assert score.duplicate_ratio == 0.0
    assert score.dimension_coverage == 1.0
    assert score.missing_dimensions == ()


def test_score_questions_bad_output():
    questions = [
        "Você deve tomar antibiótico?",
        "Quando a dor começou? Ela piora à noite?",
    ]

    score = bench_scoring.score_questions(questions, "en", ["onset", "severity"])

    assert score.question_count == 2
    assert score.count_valid is False
    assert score.single_question_ratio == 0.5
    assert score.language_match_ratio == 0.0
    assert score.language_matches is False
    assert "voce deve tomar" in score.banned_terms
    assert score.dimension_coverage == 0.5
    assert score.missing_dimensions == ("severity",)


def test_aggregate_quality_empty_and_mixed():
    empty = bench_scoring.aggregate_quality([])
    assert empty["calls"] == 0.0
    assert empty["count_valid_rate"] == 0.0
    assert empty["dimension_coverage"] == 0.0

    good = bench_scoring.score_questions(
        [
            "When did it start?",
            "What makes it worse?",
            "On a scale from 1 to 10, how severe is it?",
            "Does it spread anywhere else?",
        ],
        "en",
        ["onset", "provocation", "severity", "radiation"],
    )
    bad = bench_scoring.score_questions(
        ["Você deve tomar antibiótico?", "Quando a dor começou?"],
        "en",
        ["onset", "severity"],
    )
    aggregate = bench_scoring.aggregate_quality([good, bad])

    assert aggregate["calls"] == 2.0
    assert aggregate["count_valid_rate"] == 0.5
    assert aggregate["banned_rate"] == 0.5
    assert aggregate["language_match_ratio"] == 0.5
    assert aggregate["dimension_coverage"] == pytest.approx(0.75)
    assert aggregate["single_question_ratio"] == 1.0
    assert aggregate["avg_question_count"] == 3.0


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def test_known_model_price_and_cost():
    price = bench_pricing.get_price("gemini-2.5-flash")

    assert price.as_of == bench_pricing.PRICING_AS_OF
    assert price.input_per_million_usd == pytest.approx(0.30)
    assert price.output_per_million_usd == pytest.approx(2.50)
    assert bench_pricing.estimate_cost_usd(
        "gemini-2.5-flash", 1_000_000, 1_000_000
    ) == pytest.approx(2.80)


def test_haiku_price_and_fake_zero_cost():
    assert bench_pricing.estimate_cost_usd(
        "us.anthropic.claude-haiku-4-5-20251001-v1:0", 1_000_000, 1_000_000
    ) == pytest.approx(6.00)
    assert (
        bench_pricing.estimate_cost_usd("fake-deterministic", 1_000_000, 1_000_000)
        == 0.0
    )


def test_every_fake_model_is_free():
    for model in bench_pricing.FAKE_MODELS:
        price = bench_pricing.get_price(model)
        assert price.input_per_million_usd == 0.0
        assert price.output_per_million_usd == 0.0


def test_unknown_model_raises_instead_of_guessing():
    with pytest.raises(bench_pricing.UnknownModelError) as exc_info:
        bench_pricing.get_price("mystery-model-9000")

    message = str(exc_info.value)
    assert "mystery-model-9000" in message
    assert "Refusing to guess" in message
    assert bench_pricing.PRICING_AS_OF in message

    with pytest.raises(bench_pricing.UnknownModelError):
        bench_pricing.estimate_cost_usd("mystery-model-9000", 10, 10)


def test_negative_token_counts_are_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        bench_pricing.estimate_cost_usd("gemini-2.5-flash", -1, 10)


def test_format_usd_keeps_sub_cent_costs_visible():
    assert bench_pricing.format_usd(0.000123) == "$0.000123"


# ---------------------------------------------------------------------------
# Fixture integrity: the harness's input is synthetic and well-formed
# ---------------------------------------------------------------------------


def _fixtures() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_fixture_file_is_synthetic_and_balanced():
    payload = _fixtures()
    complaints = payload["complaints"]

    assert payload["synthetic"] is True
    assert len(complaints) == 20
    assert all(complaint["synthetic"] is True for complaint in complaints)
    assert [complaint["lang"] for complaint in complaints].count("en") == 10
    assert [complaint["lang"] for complaint in complaints].count("pt") == 10
    assert len({complaint["id"] for complaint in complaints}) == len(complaints)


def test_every_fixture_has_valid_dimensions_and_session_fields():
    required_fields = {
        "age_bracket",
        "sex",
        "specialist",
        "chief_complaint",
        "duration",
        "complaint_detail",
        "conditions",
        "medications",
        "allergies",
        "family_history",
        "smoking",
        "alcohol",
    }

    for complaint in _fixtures()["complaints"]:
        assert required_fields <= set(complaint["session"]), complaint["id"]
        expected = complaint["expected_dimensions"]
        assert 3 <= len(expected) <= 5, complaint["id"]
        assert set(expected) <= set(bench_scoring.KNOWN_DIMENSIONS), complaint["id"]


def test_fixture_records_contain_no_patient_identifiers_or_emergency_copy():
    forbidden_keys = {
        "name",
        "patient_name",
        "mrn",
        "dob",
        "email",
        "phone",
        "address",
    }
    emergency_tokens = ("emergency", "911", "urgência", "urgencia")

    for complaint in _fixtures()["complaints"]:
        assert not (forbidden_keys & set(complaint)), complaint["id"]
        assert not (forbidden_keys & set(complaint["session"])), complaint["id"]
        complaint_text = json.dumps(complaint, ensure_ascii=False).casefold()
        assert not any(token in complaint_text for token in emergency_tokens), (
            complaint["id"]
        )
