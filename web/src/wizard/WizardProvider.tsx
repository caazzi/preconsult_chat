import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Lang } from "../contracts/i18n";

export const STEP_LANDING = 0;
export const STEP_QA = 5;
export const STEP_SUMMARY = 6;

export type WizardData = {
  // Step 1 — Demographics
  ageBracket: string;
  gender: string;
  // Step 2 — Chief Complaint
  specialist: string;
  chiefComplaint: string;
  duration: string;
  complaintDetail: string;
  // Step 3 — Medical History
  conditions: string[];
  medications: string[];
  allergiesFlag: boolean;
  allergiesText: string;
  // Step 4 — Lifestyle
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

type WizardContextValue = {
  lang: Lang;
  step: number;
  data: WizardData;
  sessionId: string;
  questions: string[];
  answers: string[];
  isEmergency: boolean;
  emergencyText: string;
  loading: boolean;
  error: string;
  setStep: (step: number) => void;
  update: <K extends keyof WizardData>(key: K, value: WizardData[K]) => void;
  toggle: (key: "conditions" | "familyHistory", value: string) => void;
  setSessionId: (id: string) => void;
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
  const [questions] = useState<string[]>([]);
  const [answers] = useState<string[]>([]);
  const [isEmergency] = useState(false);
  const [emergencyText] = useState("");
  const [loading] = useState(false);
  const [error] = useState("");

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

  const reset = useCallback(() => {
    setStep(STEP_LANDING);
    setData(EMPTY_DATA);
    setSessionId("");
  }, []);

  const value = useMemo<WizardContextValue>(
    () => ({
      lang,
      step,
      data,
      sessionId,
      questions,
      answers,
      isEmergency,
      emergencyText,
      loading,
      error,
      setStep,
      update,
      toggle,
      setSessionId,
      reset,
    }),
    [
      lang,
      step,
      data,
      sessionId,
      questions,
      answers,
      isEmergency,
      emergencyText,
      loading,
      error,
      update,
      toggle,
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
