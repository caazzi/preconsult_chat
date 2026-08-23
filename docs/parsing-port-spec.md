# Question & Emergency Parsing — Port Specification

Purpose: a **framework-neutral specification** so a future non-Python frontend
(TS/JS) can implement `split_questions` and `is_emergency_trigger` as a 1:1 port
of `src/preconsult/core/parsing.py`, verified against the test matrix below.

The Python source is **the single source of truth**; this document states the
observable behavior in prose + table form, and the authoritative test suite is
`tests/test_question_parsing.py`. Any change to behavior must update both.

---

## 1. `split_questions(buffer: str) -> string[]`

Cumulative SSE buffer → ordered list of questions.

### Algorithm (reference)

```python
import re
qs = [q.strip() for q in re.split(r'\n(?:\d+[\.\)]|\-)\s*', '\n' + buffer) if q.strip()]
if len(qs) <= 1:
    qs = [q.strip() for q in buffer.strip().split('\n') if q.strip()]
return qs
```

### Behavior table

| Case | Input (buffer) | Expected output |
|---|---|---|
| Numbered dot | `\n1. One?\n2. Two?` | `["One?", "Two?"]` |
| Numbered paren | `1) One?\n2) Two?` | `["One?", "Two?"]` |
| Dash-prefixed | `- One?\n- Two?` | `["One?", "Two?"]` |
| Plain newline fallback | `One?\nTwo?` | `["One?", "Two?"]` |
| Single question | `Just one?` | `["Just one?"]` |
| Empty / whitespace | `""`, `"   "` | `[]` |
| CRLF | `1. One?\r\n2. Two?` | `["One?", "Two?"]` |
| Multiple trailing newlines | `\n1. One?\n2. Two?\n\n\n` | `["One?", "Two?"]` |
| Mixed separators | `\n1. One?\n- Two?\n3) Three?` | `["One?", "Two?", "Three?"]` |
| Leading spaces after marker | `\n1.   One?\n2.    Two?` | `["One?", "Two?"]` |
| Multi-line question body | `\n1. One long\nquestion?\n2. Two?` | `["One long\nquestion?", "Two?"]` |
| Accumulated reassembly | split mid-word, re-parse each | converges to the full final set |

### Rules

- Splits markers **only at a newline** followed by `digits + . or )` or `-`,
  then optional whitespace. A bare sequence of numbers without a preceding
  newline does NOT split.
- Each part is `strip()`ped of leading/trailing whitespace; blank parts dropped.
- If the numbered/dash split yields ≤1 element, fall back to splitting on
  every newline and stripping.
- Never returns bare numeric prefixes as questions once a full stream assembles.

---

## 2. `is_emergency_trigger(text: string) -> boolean`

True if the accumulated buffer signals a safety red flag.

### Trigger tokens (case-insensitive substring match)

- `emergency`
- `911`
- `emergência` (accented) / `emergencia` (unaccented)
- `urgência` (accented) / `urgencia` (unaccented)

### Behavior table (all covered in tests)

| Input | Expected |
|---|---|
| `"EMERGENCY: call 911"` | `true` |
| `"please dial 911 now"` | `true` |
| `"[ALERTA DE EMERGÊNCIA] ligue 192"` | `true` |
| `"urgencia nao mencionada"` | `true` |
| `"Urgência"` / `"URGENCIA"` | `true` |
| `"1. Question one?\n2. Question two?"` | `false` |
| `""` | `false` |
| `"please ring my doctor today"` | `false` |
| `"session id 1234"` | `false` |
| `"the patient is fine"` | `false` |

### Rules

- Matching is **case-insensitive** and **accent-insensitive for PT**; a TS port
  should lowercase (`toLowerCase()`) and use `includes()`. Unicode normalization
  is NOT required — the unaccented variants are listed explicitly.
- Substring match on tokens; unrelated substrings (e.g. a number like `1234`)
  must not collide.

---

## 3. Minimum TS port sketch (for implementers)

```ts
export function splitQuestions(buffer: string): string[] {
  let qs = buffer
    /* number+dot, number+paren, or dash at line start */
    .replace(/^/, '\n')
    .split(/\n(?:\d+[.)]|-)\s*/)
    .map((q) => q.trim())
    .filter(Boolean);
  if (qs.length <= 1) {
    qs = buffer.trim().split('\n').map((q) => q.trim()).filter(Boolean);
  }
  return qs;
}

const EMERGENCY = ['emergency','911','emergência','emergencia','urgência','urgencia'];
export function isEmergencyTrigger(text: string): boolean {
  const lower = text.toLowerCase();
  return EMERGENCY.some((token) => lower.includes(token));
}
```

> Validate the TS port against the behavior tables in this file (or re-run the
> equivalent of `tests/test_question_parsing.py`).
