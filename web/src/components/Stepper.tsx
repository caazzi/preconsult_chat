import { useI18n } from "../i18n/I18nProvider";
import { useWizard, STEP_SUMMARY } from "../wizard/WizardProvider";

const TOTAL = 5;

export function Stepper() {
  const { t } = useI18n();
  const { step } = useWizard();

  const activeIndex = step <= 0 ? 0 : step >= STEP_SUMMARY ? 4 : step - 1;
  const activeNumber = step <= 0 ? 1 : step >= STEP_SUMMARY ? 5 : step;

  return (
    <div className="w-full pb-4">
      {/* Mobile progress */}
      <div className="w-full space-y-2 md:hidden">
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>
            {t.step_indicator}{" "}
            <span className="font-bold text-cyan-300">{activeNumber}</span>{" "}
            {t.of_indicator} {TOTAL}
          </span>
        </div>
        <div
          role="progressbar"
          aria-label="Overall intake progress"
          aria-valuenow={Math.round((step / TOTAL) * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-1.5 w-full overflow-hidden rounded-full bg-white/10"
        >
          <div
            className="h-full rounded-full bg-cyan-400 transition-all"
            style={{ width: `${Math.min(Math.max((step / TOTAL) * 100, 0), 100)}%` }}
          />
        </div>
      </div>

      {/* Desktop stepper */}
      <div className="hidden items-center justify-between md:flex">
        {Array.from({ length: TOTAL }).map((_, idx) => {
          const isActive = activeIndex === idx && step < STEP_SUMMARY;
          const isCompleted = activeIndex > idx || step >= STEP_SUMMARY;
          const label = t.step_names[idx] ?? "";
          return (
            <div key={idx} className="flex flex-1 items-center">
              <div className="flex flex-shrink-0 items-center gap-2">
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold transition-all ${
                    isActive
                      ? "border-cyan-300 bg-cyan-300/25 text-cyan-200"
                      : isCompleted
                        ? "border-cyan-500 bg-cyan-500/40 text-cyan-100"
                        : "border-white/20 bg-white/5 text-white/50"
                  }`}
                >
                  {isCompleted ? "✓" : idx + 1}
                </span>
                <span
                  className={`whitespace-nowrap text-sm ${
                    isActive
                      ? "font-bold text-white"
                      : isCompleted
                        ? "text-slate-200"
                        : "text-white/40"
                  }`}
                >
                  {label}
                </span>
              </div>
              {idx < TOTAL - 1 && (
                <span
                  className={`mx-1 h-0.5 flex-1 ${
                    isCompleted
                      ? "bg-gradient-to-r from-cyan-500 to-cyan-300"
                      : "bg-white/10"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
