import { describe, expect, it } from "vitest";

import { buildSessionInitPayload, localizeValue } from "./payload";
import { getTranslations } from "../contracts/i18n";

const en = getTranslations("en");
const pt = getTranslations("pt");

describe("localizeValue", () => {
  it("maps an enum key to its translated label", () => {
    expect(localizeValue(en, "duration", "weeks")).toBe("Weeks");
    expect(localizeValue(pt, "smoking", "never")).toBe(pt.smoking_opts[0]);
  });

  it("returns the key unchanged when unknown, and empty for empty", () => {
    expect(localizeValue(en, "duration", "decades")).toBe("decades");
    expect(localizeValue(en, "duration", "")).toBe("");
  });
});

describe("buildSessionInitPayload", () => {
  const input = {
    ageBracket: "26-35",
    gender: "Female",
    specialist: "Cardiologist",
    chiefComplaint: "chest pain",
    duration: "weeks",
    complaintDetail: "",
    conditions: ["asthma", "diabetes"],
    medications: ["Losartan 50mg", "   ", ""],
    allergiesFlag: false,
    allergiesText: "ignored when flag is false",
    familyHistory: ["cancer"],
    smoking: "former",
    alcohol: "rarely",
  };

  it("maps fields, localizes enums, drops blank medications, sets None allergies", () => {
    const p = buildSessionInitPayload(input, "en", en);
    expect(p.age_bracket).toBe("26-35");
    expect(p.sex).toBe("Female");
    expect(p.lang).toBe("en");
    expect(p.duration).toBe(en.duration_opts[2]);
    expect(p.conditions).toEqual([en.conditions_opts[0], en.conditions_opts[2]]);
    expect(p.medications).toEqual(["Losartan 50mg"]);
    expect(p.allergies).toBe("None");
    expect(p.family_history).toEqual([en.family_history_opts[1]]);
    expect(p.smoking).toBe(en.smoking_opts[1]);
    expect(p.alcohol).toBe(en.alcohol_opts[1]);
  });

  it("passes allergy text through when the flag is true", () => {
    const p = buildSessionInitPayload(
      { ...input, allergiesFlag: true, allergiesText: "penicillin" },
      "en",
      en,
    );
    expect(p.allergies).toBe("penicillin");
  });

  it("localizes into Portuguese", () => {
    const p = buildSessionInitPayload(input, "pt", pt);
    expect(p.duration).toBe(pt.duration_opts[2]);
    expect(p.smoking).toBe(pt.smoking_opts[1]);
  });
});
