import { useI18n } from "../i18n/I18nProvider";
import {
  useWizard,
  STEP_SUMMARY,
} from "../wizard/WizardProvider";
import { ErrorCallout } from "../components/FormStepLayout";

/** Step 5 (Q&A) and Step 6 (summary) views for the shadow SPA. */
export function WizardStep() {
  const { t } = useI18n();
  const {
    step,
    questions,
    answers,
    isEmergency,
    emergencyText,
    error,
    loading,
    setAnswer,
    reloadQuestions,
    submitAnswers,
    reset,
  } = useWizard();

  if (isEmergency) {
    return (
      <div
        role="alertdialog"
        aria-label={t.emergency_title}
        className="space-y-3 rounded-xl border border-red-500/50 bg-red-950/40 p-4 text-center"
      >
        <h2 className="text-lg font-bold text-red-400">{t.emergency_title}</h2>
        <p className="font-bold text-red-300">{emergencyText}</p>
        <p className="text-sm text-slate-300">{t.emergency_body}</p>
        <a
          href="/"
          className="inline-block min-h-[48px] w-full rounded-lg bg-red-600 px-4 py-3 font-semibold text-white"
        >
          {t.emergency_cta}
        </a>
      </div>
    );
  }

  if (step === STEP_SUMMARY) {
    return (
      <div className="space-y-4">
        <h2 className="text-center text-2xl font-bold text-slate-100">
          {t.complete_title}
        </h2>
        <p className="text-center text-slate-400">{t.complete_desc}</p>
        <button
          type="button"
          onClick={reset}
          className="min-h-[48px] w-full rounded-lg border border-white/20 px-4 py-2 text-slate-200 hover:bg-white/5"
        >
          {t.start_new}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <ErrorCallout message={error} />
      <h2 className="font-semibold text-slate-100">{t.step_4}</h2>
      {loading && questions.length === 0 && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-16 w-full animate-pulse rounded-lg bg-white/5"
            />
          ))}
        </div>
      )}
      <div className="max-h-[380px] space-y-3 overflow-y-auto pr-1">
        {questions.map((q, idx) => (
          <div key={idx} className="space-y-2">
            <p className="text-xs font-bold text-slate-400">
              {idx + 1} / {questions.length}
            </p>
            <p className="font-bold text-slate-100">{q}</p>
            <textarea
              aria-label="Answer for clinical question"
              placeholder={t.answers_ph}
              value={answers[idx] ?? ""}
              onChange={(e) => setAnswer(idx, e.target.value)}
              className="min-h-[80px] w-full rounded-lg border border-white/20 bg-slate-900 p-3 text-slate-100"
            />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => void reloadQuestions()}
          disabled={loading}
          aria-label={t.step_4}
          className="min-h-[48px] rounded-lg border border-white/20 px-4 py-2 text-slate-200 hover:bg-white/5 disabled:opacity-60"
        >
          ↻
        </button>
        <button
          type="button"
          onClick={submitAnswers}
          disabled={loading}
          className="min-h-[48px] rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
        >
          {t.submit_continue}
        </button>
      </div>
    </div>
  );
}
