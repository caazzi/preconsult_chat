import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Lang, Translation } from "../contracts/i18n";
import { getTranslations } from "../contracts/i18n";
import { ApiError } from "../api/client";
import { initSession } from "../api/session";
import { logEvent } from "../api/analytics";
import { buildSessionInitPayload } from "./payload";

export const STEP_LANDING = 0;
export const STEP_DEMOGRAPHICS = 1;
export const STEP_COMPLAINT = 2;
export const STEP_HISTORY = 3;
export const STEP_LIFESTYLE = 4;
export const STEP_QA = 5;
export const STEP_SUMMARY = 6;

export type WizardData = {
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

const EMPTY_DATA: WizardData = {
  ageBracket: "",
  gender: "",
  specialist: "",
  chiefComplaint: "",
  duration: "",
  complaintDetail: "",
  conditions: [],
  medications: [],
  allergiesFlag: false,
  allergiesText: "",
  familyHistory: [],
  smoking: "",
  alcohol: "",
};

function messageForCode(code: string, t: Translation): string {
  switch (code) {
    case "rate_limited":
    case "redis_quota_exceeded":
      return t.err_rate_limit;
    case "session_expired":
      return t.err_init;
    case "network_error":
    case "service_unavailable":
    case "redis_unavailable":
      return t.err_generic;
    default:
      return t.err_init;
  }
}

type WizardContextValue = {
  lang: Lang;
  step: number;
  data: WizardData;
  sessionId: string;
  answers: string[];
  isEmergency: boolean;
  emergencyText: string;
  loading: boolean;
  error: string;
  setStep: (step: number) => void;
  update: <K extends keyof WizardData>(key: K, value: WizardData[K]) => void;
  toggle: (key: "conditions" | "familyHistory", value: string) => void;
  addMedication: () => void;
  updateMedication: (idx: number, value: string) => void;
  removeMedication: (idx: number) => void;
  setAnswer: (idx: number, value: string) => void;
  clearError: () => void;
  goBack: () => void;
  goToComplaint: () => void;
  goToHistory: () => void;
  goToLifestyle: () => void;
  startSession: () => Promise<void>;
  reset: () => void;
};

const WizardContext = createContext<WizardContextValue | null>(null);

export function WizardProvider({
  lang,
  children,
}: {
  lang: Lang;
  children: ReactNode;
}) {
  const [step, setStep] = useState(STEP_LANDING);
  const [data, setData] = useState<WizardData>(EMPTY_DATA);
  const [sessionId, setSessionId] = useState("");
  const [answers, setAnswers] = useState<string[]>([]);
  const [isEmergency, setIsEmergency] = useState(false);
  const [emergencyText, setEmergencyText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const t = useMemo(() => getTranslations(lang), [lang]);

  const update = useCallback(
    <K extends keyof WizardData>(key: K, value: WizardData[K]) => {
      setData((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const toggle = useCallback(
    (key: "conditions" | "familyHistory", value: string) => {
      setData((prev) => {
        const list = prev[key];
        const next = list.includes(value)
          ? list.filter((v) => v !== value)
          : [...list, value];
        return { ...prev, [key]: next };
      });
    },
    [],
  );

  const addMedication = useCallback(() => {
    setData((prev) => ({ ...prev, medications: [...prev.medications, ""] }));
  }, []);

  const updateMedication = useCallback((idx: number, value: string) => {
    setData((prev) => {
      const meds = [...prev.medications];
      meds[idx] = value;
      return { ...prev, medications: meds };
    });
  }, []);

  const removeMedication = useCallback((idx: number) => {
    setData((prev) => ({
      ...prev,
      medications: prev.medications.filter((_, i) => i !== idx),
    }));
  }, []);

  const setAnswer = useCallback((idx: number, value: string) => {
    setAnswers((prev) => {
      const next = [...prev];
      while (next.length <= idx) next.push("");
      next[idx] = value;
      return next;
    });
  }, []);

  const clearError = useCallback(() => setError(""), []);

  const goBack = useCallback(() => {
    setStep((s) => Math.max(s - 1, 0));
    setError("");
  }, []);

  const goToComplaint = useCallback(() => {
    setData((prev) => {
      if (!prev.gender.trim()) {
        setError(t.err_gender);
        return prev;
      }
      setError("");
      setStep(STEP_COMPLAINT);
      return prev;
    });
  }, [t]);

  const goToHistory = useCallback(() => {
    setData((prev) => {
      if (!prev.specialist.trim() || !prev.chiefComplaint.trim()) {
        setError(t.err_chief_complaint);
        return prev;
      }
      setError("");
      setStep(STEP_HISTORY);
      return prev;
    });
  }, [t]);

  const goToLifestyle = useCallback(() => {
    setError("");
    setStep(STEP_LIFESTYLE);
  }, []);

  const startSession = useCallback(async () => {
    setLoading(true);
    setError("");
    const payload = buildSessionInitPayload(data, lang, t);
    try {
      const id = await initSession(payload);
      setSessionId(id);
      setAnswers([]);
      setStep(STEP_QA);
      logEvent("lifestyle_submitted", id);
    } catch (e) {
      const code = e instanceof ApiError ? e.code : "internal_error";
      setError(messageForCode(code, t));
    } finally {
      setLoading(false);
    }
  }, [data, lang, t]);

  const reset = useCallback(() => {
    setStep(STEP_LANDING);
    setData(EMPTY_DATA);
    setSessionId("");
    setAnswers([]);
    setIsEmergency(false);
    setEmergencyText("");
    setError("");
    setLoading(false);
  }, []);

  const value = useMemo<WizardContextValue>(
    () => ({
      lang,
      step,
      data,
      sessionId,
      answers,
      isEmergency,
      emergencyText,
      loading,
      error,
      setStep,
      update,
      toggle,
      addMedication,
      updateMedication,
      removeMedication,
      setAnswer,
      clearError,
      goBack,
      goToComplaint,
      goToHistory,
      goToLifestyle,
      startSession,
      reset,
    }),
    [
      lang,
      step,
      data,
      sessionId,
      answers,
      isEmergency,
      emergencyText,
      loading,
      error,
      update,
      toggle,
      addMedication,
      updateMedication,
      removeMedication,
      setAnswer,
      clearError,
      goBack,
      goToComplaint,
      goToHistory,
      goToLifestyle,
      startSession,
      reset,
    ],
  );

  return (
    <WizardContext.Provider value={value}>{children}</WizardContext.Provider>
  );
}

export function useWizard(): WizardContextValue {
  const ctx = useContext(WizardContext);
  if (!ctx) throw new Error("useWizard must be used within a WizardProvider");
  return ctx;
}
