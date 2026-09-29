import { useState } from "react";

import { useI18n } from "../i18n/I18nProvider";

const FAQ_KEYS = [
  ["faq_q1", "faq_a1"],
  ["faq_q2", "faq_a2"],
  ["faq_q3", "faq_a3"],
  ["faq_q4", "faq_a4"],
  ["faq_q5", "faq_a5"],
] as const;

export function FaqSection() {
  const { t } = useI18n();
  const [open, setOpen] = useState<string | null>(null);

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-6">
      <hr className="border-white/10" />
      <h2 className="mt-4 text-center text-lg font-semibold text-slate-100">
        {t.faq_title}
      </h2>
      <div className="mt-4 space-y-2">
        {FAQ_KEYS.map(([q, a]) => {
          const isOpen = open === q;
          return (
            <div
              key={q}
              className="rounded-lg border border-white/10"
            >
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : q)}
                className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-bold text-slate-100 hover:bg-cyan-400/5"
              >
                <span>{t[q]}</span>
                <span aria-hidden className="text-slate-400">
                  {isOpen ? "−" : "+"}
                </span>
              </button>
              {isOpen && (
                <p className="px-4 pb-3 text-sm text-slate-400">{t[a]}</p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
