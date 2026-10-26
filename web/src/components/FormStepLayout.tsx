import type { ReactNode } from "react";

import { useI18n } from "../i18n/I18nProvider";

export function ErrorCallout({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="mb-3 w-full rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300"
    >
      {message}
    </div>
  );
}

export function FormStepLayout({
  title,
  description,
  children,
  onBack,
  onNext,
  nextLabel,
  nextLoading = false,
}: {
  title: string;
  description: string;
  children: ReactNode;
  onBack: () => void;
  onNext: () => void;
  nextLabel: string;
  nextLoading?: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="w-full space-y-4">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
        <p className="text-sm text-slate-400">{description}</p>
        <hr className="border-white/10" />
      </div>
      {children}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={onBack}
          className="min-h-[48px] rounded-lg border border-white/20 px-4 py-2 text-slate-200 hover:bg-white/5"
        >
          {t.back_btn}
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={nextLoading}
          className="min-h-[48px] rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
        >
          {nextLoading ? "…" : nextLabel}
        </button>
      </div>
    </div>
  );
}
