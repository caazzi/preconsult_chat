import { useI18n } from "../i18n/I18nProvider";
import { useWizard } from "../wizard/WizardProvider";

const HOW = [
  ["message-square", "step_how_1", "step_sub_1"],
  ["brain", "step_how_2", "step_sub_2"],
  ["file-text", "step_how_3", "step_sub_3"],
] as const;

export function Landing() {
  const { t } = useI18n();
  const { startIntake } = useWizard();

  return (
    <div className="space-y-5">
      <div className="flex justify-center">
        <span className="flex items-center gap-1 rounded-full bg-green-500/10 px-3 py-1 text-xs text-green-400">
          <span aria-hidden>🛡</span>
          {t.privacy_badge_landing}
        </span>
      </div>

      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-bold leading-tight text-slate-50 sm:text-3xl">
          {t.hero_title}
        </h1>
        <p className="text-sm text-slate-400">{t.hero_subtitle}</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        {HOW.map(([icon, title, sub]) => (
          <div
            key={title}
            className="flex w-full flex-1 flex-col items-center gap-2 rounded-xl border border-white/10 p-4 text-center hover:bg-cyan-400/5"
          >
            <span aria-hidden className="text-xl">
              {icon === "message-square" ? "💬" : icon === "brain" ? "🧠" : "📄"}
            </span>
            <span className="text-sm font-bold text-slate-100">{t[title]}</span>
            <span className="text-xs text-slate-400">{t[sub]}</span>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={startIntake}
        className="min-h-[48px] w-full rounded-lg bg-cyan-500 px-4 py-3 font-semibold text-slate-950 transition hover:scale-[1.01] hover:bg-cyan-400"
      >
        {t.start_cta}
      </button>
    </div>
  );
}
