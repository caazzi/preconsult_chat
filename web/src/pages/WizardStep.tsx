import { useI18n } from "../i18n/I18nProvider";
import { useWizard } from "../wizard/WizardProvider";

/**
 * Placeholder for the wizard steps. The full form (2.1.2), SSE interview
 * (2.1.3) and PDF summary (2.1.4) land in later commits; this keeps the shell
 * navigable and the stepper exercised.
 */
export function WizardStep() {
  const { t } = useI18n();
  const { step, setStep, data } = useWizard();

  const titles: Record<number, string> = {
    1: t.intake,
    2: t.step_1,
    3: t.step_2,
    4: t.step_3,
    5: t.step_4,
    6: t.complete_title,
  };
  const title = titles[step] ?? t.intake;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
      <pre className="overflow-x-auto rounded-lg bg-black/30 p-3 text-xs text-slate-400">
        {JSON.stringify(data, null, 2)}
      </pre>
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => setStep(Math.max(step - 1, 0))}
          className="min-h-[48px] rounded-lg border border-white/20 px-4 py-2 text-slate-200 hover:bg-white/5"
        >
          {t.back_btn}
        </button>
        <button
          type="button"
          onClick={() => setStep(step + 1)}
          className="min-h-[48px] rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-400"
        >
          {t.start_btn}
        </button>
      </div>
    </div>
  );
}
