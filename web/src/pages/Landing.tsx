import type { RefObject } from "react";

import { useI18n } from "../i18n/I18nProvider";
import { StartButton } from "../components/StartButton";

const HOW = [
  ["01", "step_how_1", "step_sub_1"],
  ["02", "step_how_2", "step_sub_2"],
  ["03", "step_how_3", "step_sub_3"],
] as const;

type LandingProps = {
  headingRef?: RefObject<HTMLHeadingElement>;
};

export function Landing({ headingRef }: LandingProps) {
  const { t } = useI18n();

  return (
    <section
      data-testid="landing-hero"
      className="mx-auto w-full max-w-5xl px-4 pb-2 pt-2 sm:pt-6"
    >
      <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-xl backdrop-blur sm:p-8 lg:p-10">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-12">
          <div>
            <span className="inline-flex items-center rounded-xl bg-green-500/10 px-3 py-1 text-center text-xs font-medium leading-snug text-green-300 sm:rounded-full">
              {t.privacy_badge_landing}
            </span>

            <h1
              ref={headingRef}
              tabIndex={-1}
              className="mt-5 text-balance text-3xl font-bold leading-tight tracking-tight text-slate-50 outline-none sm:text-4xl"
            >
              {t.hero_title}
            </h1>
            <p className="mt-3 max-w-xl text-pretty text-base leading-relaxed text-slate-400">
              {t.hero_subtitle}
            </p>

            <StartButton className="mt-6 w-full sm:w-auto" />
            <p className="mt-3 text-xs text-slate-400">{t.landing_meta}</p>
          </div>

          <div className="lg:pl-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
              {t.how_title}
            </h2>
            <ol className="mt-5">
              {HOW.map(([number, title, sub], index) => (
                <li key={title} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <span
                      aria-hidden
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-xs font-bold text-cyan-200"
                    >
                      {number}
                    </span>
                    {index < HOW.length - 1 && (
                      <span
                        aria-hidden
                        className="mt-1 w-px flex-1 bg-white/10"
                      />
                    )}
                  </div>
                  <div className={index < HOW.length - 1 ? "pb-6" : ""}>
                    <p className="text-sm font-bold text-slate-100">
                      {t[title]}
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-400">
                      {t[sub]}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
}
