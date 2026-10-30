import { useState } from "react";

import { StartButton } from "./StartButton";
import { useI18n } from "../i18n/I18nProvider";

const FAQ_KEYS = [
  ["faq_q1", "faq_a1"],
  ["faq_q2", "faq_a2"],
  ["faq_q3", "faq_a3"],
  ["faq_q4", "faq_a4"],
  ["faq_q5", "faq_a5"],
] as const;

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${
        open ? "rotate-180" : ""
      }`}
    >
      <path d="m5 7.5 5 5 5-5" />
    </svg>
  );
}

export function FaqSection() {
  const { t } = useI18n();
  const [open, setOpen] = useState<string | null>(FAQ_KEYS[0][0]);

  return (
    <section
      data-testid="faq"
      aria-labelledby="faq-heading"
      className="mx-auto w-full max-w-3xl px-4 pb-16 pt-10 sm:pt-12"
    >
      <div className="border-t border-white/10 pt-8">
        <h2
          id="faq-heading"
          className="text-xl font-semibold tracking-tight text-slate-50 sm:text-2xl"
        >
          {t.faq_title}
        </h2>

        <div className="mt-5 space-y-2">
          {FAQ_KEYS.map(([q, a]) => {
            const isOpen = open === q;
            const panelId = `faq-panel-${q}`;
            const buttonId = `faq-button-${q}`;
            return (
              <div
                key={q}
                className="overflow-hidden rounded-xl border border-white/10 bg-slate-900/40"
              >
                <h3>
                  <button
                    id={buttonId}
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpen(isOpen ? null : q)}
                    className="flex min-h-[48px] w-full items-center justify-between gap-4 px-4 py-3 text-left text-sm font-bold text-slate-100 transition hover:bg-cyan-400/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cyan-300"
                  >
                    <span>{t[q]}</span>
                    <ChevronIcon open={isOpen} />
                  </button>
                </h3>
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  hidden={!isOpen}
                >
                  <p className="px-4 pb-4 text-sm leading-relaxed text-slate-400">
                    {t[a]}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-8 text-center">
          <StartButton className="w-full sm:w-auto" />
        </div>
      </div>
    </section>
  );
}
