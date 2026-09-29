// Pure port of reflex_app/preconsult/state.py::build_session_init_payload.
//
// Field mapping, localization of enum keys, filtering of blank medication
// entries, and the allergies "None" fallback are preserved exactly. Kept pure
// (no React) so it is unit-testable in isolation.

import type { Lang, Translation } from "../contracts/i18n";
import { getTranslations } from "../contracts/i18n";

const KEYS = {
  duration: ["today", "days", "weeks", "months", "years"],
  conditions: ["asthma", "depression", "diabetes", "hypertension", "thyroid"],
  familyHistory: ["alzheimers", "cancer", "diabetes", "heart"],
  smoking: ["never", "former", "current"],
  alcohol: ["never", "rarely", "socially", "frequently"],
} as const;

const OPT_FIELDS = {
  duration: "duration_opts",
  conditions: "conditions_opts",
  familyHistory: "family_history_opts",
  smoking: "smoking_opts",
  alcohol: "alcohol_opts",
} as const;

type Category = keyof typeof KEYS;

/** Localize an enum key (e.g. "weeks") to its translated label. */
export function localizeValue(
  t: Translation,
  category: Category,
  key: string,
): string {
  if (!key) return "";
  const keys = KEYS[category];
  const idx = (keys as readonly string[]).indexOf(key);
  if (idx < 0) return key;
  const opts = t[OPT_FIELDS[category]] as string[];
  return idx < opts.length ? opts[idx] : key;
}

export type SessionInitInput = {
  ageBracket: string;
  gender: string;
  specialist: string;
  chiefComplaint: string;
  duration: string;
  complaintDetail: string;
  conditions: string[];
  medications: string[];
  allergiesFlag: boolean;
  allergiesText: string;
  familyHistory: string[];
  smoking: string;
  alcohol: string;
};

export type SessionInitPayload = {
  age_bracket: string;
  sex: string;
  lang: Lang;
  specialist: string;
  chief_complaint: string;
  duration: string;
  complaint_detail: string;
  conditions: string[];
  medications: string[];
  allergies: string;
  family_history: string[];
  smoking: string;
  alcohol: string;
};

export function buildSessionInitPayload(
  input: SessionInitInput,
  lang: Lang,
  t: Translation = getTranslations(lang),
): SessionInitPayload {
  return {
    age_bracket: input.ageBracket,
    sex: input.gender,
    lang,
    specialist: input.specialist,
    chief_complaint: input.chiefComplaint,
    duration: localizeValue(t, "duration", input.duration),
    complaint_detail: input.complaintDetail,
    conditions: input.conditions.map((c) => localizeValue(t, "conditions", c)),
    medications: input.medications.filter((m) => m.trim() !== ""),
    allergies: input.allergiesFlag ? input.allergiesText : "None",
    family_history: input.familyHistory.map((f) =>
      localizeValue(t, "familyHistory", f),
    ),
    smoking: localizeValue(t, "smoking", input.smoking),
    alcohol: localizeValue(t, "alcohol", input.alcohol),
  };
}
