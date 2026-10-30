import { useI18n } from "../i18n/I18nProvider";
import { useWizard } from "../wizard/WizardProvider";

type StartButtonProps = {
  className?: string;
};

/** The landing's single entry point, reused by the hero and the FAQ closing CTA. */
export function StartButton({ className = "" }: StartButtonProps) {
  const { t } = useI18n();
  const { startIntake } = useWizard();

  return (
    <button
      type="button"
      onClick={startIntake}
      className={`min-h-[48px] rounded-lg bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-300 ${className}`}
    >
      {t.start_cta}
    </button>
  );
}
