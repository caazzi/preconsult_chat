"""Deterministic, offline quality scoring for interview-question output.

No LLM judge, no network, no provider SDK, no app imports. Every function is a
pure heuristic so the same text always scores the same way and a regression
cannot be hidden behind a second model call.

The rubric asks a narrow question: *did the model produce usable intake
questions for this synthetic complaint?* It is not a clinical correctness
score.

Dimensions are the OPQRST/SAMPLE axes a good intake should probe. Fixtures list
the ones that matter for their complaint, and coverage is measured against that
list rather than against every possible dimension.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

OPQRST_DIMENSIONS: tuple[str, ...] = (
    "onset",
    "provocation",
    "palliation",
    "quality",
    "region",
    "radiation",
    "severity",
    "timing",
)

SAMPLE_DIMENSIONS: tuple[str, ...] = (
    "associated",
    "allergies",
    "medications",
    "past_history",
    "last_intake",
    "events",
)

KNOWN_DIMENSIONS: tuple[str, ...] = OPQRST_DIMENSIONS + SAMPLE_DIMENSIONS

# Keywords are stored accent-free and lowercase; inputs are normalized the same
# way before matching, so "frequência" and "frequencia" behave identically.
# A question may cover several dimensions ("Where does it hurt and does it
# spread?") -- overlap is a feature, not double counting, because each expected
# dimension is answered independently.
DIMENSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "onset": (
        "when did",
        "when does",
        "how long",
        "how long ago",
        "start",
        "started",
        "starts",
        "begin",
        "began",
        "begins",
        "first notice",
        "first noticed",
        "onset",
        "quando",
        "quanto tempo",
        "ha quanto tempo",
        "comecou",
        "comeca",
        "comecar",
        "inicio",
        "desde quando",
    ),
    "provocation": (
        "makes it worse",
        "makes the pain worse",
        "makes the discomfort worse",
        "worse when",
        "worse with",
        "what triggers",
        "trigger",
        "aggravate",
        "worse",
        "piora",
        "piorar",
        "o que faz piorar",
        "agrava",
        "desencadeia",
        "gatilho",
        "pior quando",
    ),
    "palliation": (
        "makes it better",
        "makes the pain better",
        "makes the discomfort better",
        "better when",
        "relieve",
        "relieves",
        "eases",
        "improve",
        "better",
        "melhora",
        "melhorar",
        "o que faz melhorar",
        "alivia",
        "melhor quando",
    ),
    "quality": (
        "describe",
        "describes",
        "feel like",
        "sharp",
        "dull",
        "burning",
        "pressure",
        "tightness",
        "nature",
        "descreva",
        "descreve",
        "descreveria",
        "como e",
        "pontada",
        "queimacao",
        "aperto",
        "pressao",
        "latejante",
    ),
    "region": (
        "where",
        "location",
        "which part",
        "point to",
        "onde",
        "localizacao",
        "em que parte",
        "regiao",
    ),
    "radiation": (
        "spread",
        "spreads",
        "radiate",
        "radiates",
        "travel",
        "travels",
        "move to",
        "elsewhere",
        "espalha",
        "irradia",
        "para outro lugar",
        "outro lugar",
    ),
    "severity": (
        "scale",
        "1 to 10",
        "1-10",
        "0 to 10",
        "how severe",
        "how bad",
        "intensity",
        "escala",
        "quao forte",
        "intensidade",
        "gravidade",
    ),
    "timing": (
        "how often",
        "how many times",
        "frequency",
        "constant",
        "comes and goes",
        "how long does",
        "pattern",
        "frequencia",
        "constante",
        "vai e volta",
        "duracao",
        "padrao",
    ),
    "associated": (
        "other symptoms",
        "any other",
        "along with",
        "associated",
        "also",
        "nausea",
        "vomit",
        "fever",
        "dizzy",
        "shortness of breath",
        "outros sintomas",
        "algum outro",
        "junto",
        "associado",
        "tambem",
        "nausea",
        "vomito",
        "febre",
        "tontura",
        "falta de ar",
    ),
    "allergies": (
        "allergy",
        "allergies",
        "allergic",
        "reaction to",
        "alergia",
        "alergias",
        "alergico",
        "reacao a",
    ),
    "medications": (
        "medication",
        "medications",
        "medicine",
        "medicines",
        "prescription",
        "taking any",
        "currently taking",
        "medicamento",
        "medicamentos",
        "remedio",
        "remedios",
        "tomando",
        "prescricao",
    ),
    "past_history": (
        "past",
        "history",
        "previous",
        "previously",
        "before",
        "had this",
        "condition",
        "diagnosed",
        "historico",
        "passado",
        "anterior",
        "antes",
        "ja teve",
        "condicao",
        "diagnosticado",
    ),
    "last_intake": (
        "last ate",
        "last eat",
        "last drink",
        "last drank",
        "oral intake",
        "when did you last",
        "food",
        "water",
        "ultima vez",
        "ultima refeicao",
        "comeu",
        "bebeu",
        "alimento",
        "agua",
    ),
    "events": (
        "what happened",
        "leading up",
        "before it started",
        "started after",
        "triggered by",
        "events",
        "o que aconteceu",
        "antes de",
        "comecou depois",
        "levou a",
        "eventos",
    ),
}

# Two families so a report can say *which* guardrail tripped. The lists target
# the assistant asserting a diagnosis or recommending treatment, not a patient
# history question: "Have you been diagnosed with asthma?" and "Are you taking
# any medications?" are legitimate and must not match.
BANNED_DIAGNOSIS_TERMS: tuple[str, ...] = (
    "you may have",
    "you might have",
    "you probably have",
    "you likely have",
    "it is likely that",
    "it sounds like you have",
    "this suggests",
    "this means you have",
    "i think you have",
    "the diagnosis is",
    "your diagnosis is",
    "you are suffering from",
    "provavelmente voce tem",
    "parece que voce tem",
    "isso sugere",
    "isso significa que voce tem",
    "eu acho que voce tem",
    "o diagnostico e",
    "seu diagnostico e",
    "voce esta sofrendo de",
)

BANNED_TREATMENT_TERMS: tuple[str, ...] = (
    "you should take",
    "you need to take",
    "you must take",
    "take this medication",
    "take this medicine",
    "take ibuprofen",
    "take paracetamol",
    "take aspirin",
    "start taking",
    "stop taking",
    "i recommend",
    "i can prescribe",
    "i will prescribe",
    "you need treatment",
    "you should get treatment",
    "the treatment is",
    "cure for",
    "remedy for",
    "you need surgery",
    "surgery is",
    "voce deve tomar",
    "voce precisa tomar",
    "tome este remedio",
    "tome este medicamento",
    "tome ibuprofeno",
    "tome paracetamol",
    "tome aspirina",
    "comece a tomar",
    "pare de tomar",
    "eu recomendo",
    "posso receitar",
    "vou receitar",
    "voce precisa de tratamento",
    "voce deve procurar tratamento",
    "o tratamento e",
    "cura para",
    "voce precisa de cirurgia",
    "cirurgia e",
)

BANNED_TERMS: tuple[str, ...] = BANNED_DIAGNOSIS_TERMS + BANNED_TREATMENT_TERMS

_LANGUAGE_NAMES = ("en", "pt")

_PT_ACCENT_CHARS = frozenset("ãõçáéíóúâêôà")

_EN_MARKERS = frozenset(
    {
        "allergies",
        "allergy",
        "also",
        "any",
        "are",
        "before",
        "better",
        "cough",
        "could",
        "currently",
        "describe",
        "did",
        "do",
        "does",
        "eat",
        "feel",
        "fever",
        "has",
        "have",
        "history",
        "how",
        "hurt",
        "is",
        "last",
        "long",
        "medication",
        "medications",
        "medicine",
        "often",
        "or",
        "pain",
        "rash",
        "scale",
        "severe",
        "should",
        "spread",
        "start",
        "started",
        "swelling",
        "symptom",
        "symptoms",
        "taking",
        "the",
        "this",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "why",
        "with",
        "worse",
        "would",
        "you",
        "your",
    }
)

_PT_MARKERS = frozenset(
    {
        "aconteceu",
        "agua",
        "algum",
        "alguma",
        "alergia",
        "alergias",
        "alergico",
        "antes",
        "atualmente",
        "bebeu",
        "comecou",
        "comeca",
        "comecar",
        "comeu",
        "como",
        "com",
        "constante",
        "costuma",
        "depois",
        "desde",
        "dor",
        "duracao",
        "escala",
        "espalha",
        "esta",
        "faz",
        "febre",
        "forte",
        "frequencia",
        "gravidade",
        "historico",
        "hoje",
        "inchaco",
        "inicio",
        "intensidade",
        "irradia",
        "junto",
        "melhora",
        "melhorar",
        "medicamento",
        "medicamentos",
        "nausea",
        "onde",
        "outro",
        "outros",
        "padrao",
        "para",
        "passado",
        "piora",
        "piorar",
        "pode",
        "porque",
        "qual",
        "quais",
        "quando",
        "quanto",
        "quantos",
        "quao",
        "refeicao",
        "remedio",
        "remedios",
        "sentindo",
        "sente",
        "sem",
        "sintoma",
        "sintomas",
        "sua",
        "seu",
        "tambem",
        "tem",
        "tempo",
        "teve",
        "tomando",
        "tosse",
        "ultima",
        "vezes",
        "voce",
        "vomito",
    }
)

_LEADING_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*\u2022])\s*")
_INTERROGATIVE_START = re.compile(
    r"^(?:"
    r"who|what|when|where|why|how|do|does|did|is|are|was|were|have|has|"
    r"can|could|would|should|will|"
    r"quando|onde|como|qual|quais|quanto|quantos|voce|tem|esta|sente|"
    r"pode|costuma|ha"
    r")\b"
)
_SENTENCE_BOUNDARY = re.compile(r"[.!]\s+\S")
_WORD = re.compile(r"[a-z]+")


def normalize_text(text: str) -> str:
    """Lowercase, strip diacritics and collapse whitespace.

    Punctuation is preserved: a question mark is scoring signal, not noise.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_accents.casefold().split())


def _phrase_present(haystack: str, phrase: str) -> bool:
    """Word-boundary phrase match on already-normalized text."""
    words = normalize_text(phrase).split()
    if not words:
        return False
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in words) + r"(?!\w)"
    return re.search(pattern, haystack) is not None


def question_covers_dimension(question: str, dimension: str) -> bool:
    """Whether one question probes ``dimension``."""
    if dimension not in DIMENSION_KEYWORDS:
        raise ValueError(
            f"unknown dimension {dimension!r}; known: {', '.join(KNOWN_DIMENSIONS)}"
        )
    normalized = normalize_text(question)
    return any(
        _phrase_present(normalized, keyword)
        for keyword in DIMENSION_KEYWORDS[dimension]
    )


@dataclass(frozen=True)
class DimensionCoverage:
    """How much of a fixture's expected OPQRST/SAMPLE surface was probed."""

    ratio: float
    covered: tuple[str, ...]
    missing: tuple[str, ...]
    observed: tuple[str, ...]


def dimension_coverage(
    questions: Sequence[str], expected_dimensions: Sequence[str]
) -> DimensionCoverage:
    """Measure expected-dimension coverage.

    ``observed`` lists known dimensions probed beyond the expected set, which is
    a useful "asked about the right axis for the wrong complaint" signal.
    Unknown expected dimensions raise ``ValueError`` so a fixture typo cannot
    silently lower every score.
    """
    expected = tuple(dict.fromkeys(expected_dimensions))
    unknown = [dimension for dimension in expected if dimension not in KNOWN_DIMENSIONS]
    if unknown:
        raise ValueError(
            f"unknown expected dimension(s) {unknown!r}; "
            f"known: {', '.join(KNOWN_DIMENSIONS)}"
        )

    present = [
        dimension
        for dimension in KNOWN_DIMENSIONS
        if any(question_covers_dimension(q, dimension) for q in questions)
    ]
    covered = tuple(dimension for dimension in expected if dimension in present)
    missing = tuple(dimension for dimension in expected if dimension not in present)
    observed = tuple(dimension for dimension in present if dimension not in expected)
    ratio = len(covered) / len(expected) if expected else 1.0
    return DimensionCoverage(
        ratio=ratio, covered=covered, missing=missing, observed=observed
    )


def count_is_valid(
    questions: Sequence[str], minimum: int = 3, maximum: int = 5
) -> bool:
    """The prompt/tool contract asks for 3-5 questions."""
    return minimum <= len(questions) <= maximum


def is_single_question(text: str) -> bool:
    """Heuristic for "one clear question per item".

    Rejects multiple question marks, embedded newlines and a second sentence
    before the question mark. A single unpunctuated line is accepted only when
    it starts with an interrogative, so "Tell me more" is not silently treated
    as a question.
    """
    cleaned = _LEADING_MARKER.sub("", str(text).strip())
    if not cleaned or "\n" in cleaned or "\r" in cleaned:
        return False
    if cleaned.count("?") > 1:
        return False
    if cleaned.count("?") == 0:
        return bool(_INTERROGATIVE_START.match(normalize_text(cleaned)))
    if _SENTENCE_BOUNDARY.search(cleaned):
        return False
    return True


def single_question_ratio(questions: Sequence[str]) -> float:
    """Fraction of items that look like exactly one question."""
    if not questions:
        return 0.0
    return sum(1 for question in questions if is_single_question(question)) / len(
        questions
    )


def detect_language(text: str) -> Literal["en", "pt", "unknown"]:
    """Classify one string from marker words plus Portuguese diacritics."""
    lowered = text.casefold()
    accent_bonus = 2 if any(char in _PT_ACCENT_CHARS for char in lowered) else 0
    words = _WORD.findall(normalize_text(text))
    english = sum(1 for word in words if word in _EN_MARKERS)
    portuguese = sum(1 for word in words if word in _PT_MARKERS) + accent_bonus
    if english == portuguese:
        return "unknown"
    return "en" if english > portuguese else "pt"


def language_match_ratio(questions: Sequence[str], lang: str) -> float:
    """Fraction of questions classified as the requested language."""
    if lang not in _LANGUAGE_NAMES:
        raise ValueError(f"lang must be one of {_LANGUAGE_NAMES}, got {lang!r}")
    if not questions:
        return 0.0
    return sum(1 for question in questions if detect_language(question) == lang) / len(
        questions
    )


def language_matches(
    questions: Sequence[str], lang: str, threshold: float = 0.6
) -> bool:
    """Whether enough of the list is in the requested language.

    A whole-list pass/fail would hide one stray question; the ratio is reported
    alongside this boolean so a mixed-language answer is visible.
    """
    return language_match_ratio(questions, lang) >= threshold


def _normalized_questions(questions: Iterable[str]) -> str:
    # The sentinel is non-word, so a banned phrase can never be assembled from
    # the end of one question and the start of the next.
    return normalize_text(" | ".join(str(question) for question in questions))


def banned_terms_in(questions: Sequence[str]) -> tuple[str, ...]:
    """Return the diagnosis/treatment phrases the output actually used."""
    haystack = _normalized_questions(questions)
    return tuple(term for term in BANNED_TERMS if _phrase_present(haystack, term))


def has_banned_terms(questions: Sequence[str]) -> bool:
    """Whether any diagnosis/treatment phrase appears in the list."""
    return bool(banned_terms_in(questions))


def duplicate_ratio(questions: Sequence[str]) -> float:
    """Fraction of items that repeat an earlier item (case/punctuation folded)."""
    if not questions:
        return 0.0
    seen: set[str] = set()
    duplicates = 0
    for question in questions:
        key = normalize_text(str(question)).strip(" ?!.,;:")
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates / len(questions)


@dataclass(frozen=True)
class QualityScore:
    """One call's deterministic quality metrics."""

    question_count: int
    count_valid: bool
    single_question_ratio: float
    language_match_ratio: float
    language_matches: bool
    banned_terms: tuple[str, ...]
    duplicate_ratio: float
    dimension_coverage: float
    covered_dimensions: tuple[str, ...]
    missing_dimensions: tuple[str, ...]


def score_questions(
    questions: Sequence[str],
    lang: str,
    expected_dimensions: Sequence[str],
) -> QualityScore:
    """Score one generated question list against one synthetic fixture."""
    usable = tuple(str(question) for question in questions if str(question).strip())
    coverage = dimension_coverage(usable, expected_dimensions)
    return QualityScore(
        question_count=len(usable),
        count_valid=count_is_valid(usable),
        single_question_ratio=single_question_ratio(usable),
        language_match_ratio=language_match_ratio(usable, lang),
        language_matches=language_matches(usable, lang),
        banned_terms=banned_terms_in(usable),
        duplicate_ratio=duplicate_ratio(usable),
        dimension_coverage=coverage.ratio,
        covered_dimensions=coverage.covered,
        missing_dimensions=coverage.missing,
    )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate_quality(scores: Sequence[QualityScore]) -> dict[str, float]:
    """Aggregate per-call scores for a benchmark row.

    Empty input returns zeros instead of raising: a row whose every call failed
    still needs a reportable shape.
    """
    if not scores:
        return {
            "calls": 0.0,
            "count_valid_rate": 0.0,
            "single_question_ratio": 0.0,
            "language_match_ratio": 0.0,
            "duplicate_ratio": 0.0,
            "dimension_coverage": 0.0,
            "banned_rate": 0.0,
            "avg_question_count": 0.0,
        }
    return {
        "calls": float(len(scores)),
        "count_valid_rate": _mean(
            [1.0 if score.count_valid else 0.0 for score in scores]
        ),
        "single_question_ratio": _mean(
            [score.single_question_ratio for score in scores]
        ),
        "language_match_ratio": _mean([score.language_match_ratio for score in scores]),
        "duplicate_ratio": _mean([score.duplicate_ratio for score in scores]),
        "dimension_coverage": _mean([score.dimension_coverage for score in scores]),
        "banned_rate": _mean([1.0 if score.banned_terms else 0.0 for score in scores]),
        "avg_question_count": _mean([float(score.question_count) for score in scores]),
    }


__all__ = [
    "BANNED_DIAGNOSIS_TERMS",
    "BANNED_TERMS",
    "BANNED_TREATMENT_TERMS",
    "DIMENSION_KEYWORDS",
    "KNOWN_DIMENSIONS",
    "OPQRST_DIMENSIONS",
    "SAMPLE_DIMENSIONS",
    "DimensionCoverage",
    "QualityScore",
    "aggregate_quality",
    "banned_terms_in",
    "count_is_valid",
    "detect_language",
    "dimension_coverage",
    "duplicate_ratio",
    "has_banned_terms",
    "is_single_question",
    "language_match_ratio",
    "language_matches",
    "normalize_text",
    "question_covers_dimension",
    "score_questions",
    "single_question_ratio",
]
