import { useEffect, useRef } from "react";

import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { FaqSection } from "./components/FaqSection";
import { I18nProvider, useI18n } from "./i18n/I18nProvider";
import {
  WizardProvider,
  useWizard,
  STEP_LANDING,
  STEP_DEMOGRAPHICS,
  STEP_COMPLAINT,
  STEP_HISTORY,
  STEP_LIFESTYLE,
  STEP_QA,
  STEP_SUMMARY,
} from "./wizard/WizardProvider";
import { Stepper } from "./components/Stepper";
import { Landing } from "./pages/Landing";
import { normalizePath } from "./navigation";
import {
  StepDemographics,
  StepComplaint,
  StepHistory,
  StepLifestyle,
} from "./pages/steps";
import { WizardStep } from "./pages/WizardStep";

function CurrentStep() {
  const { step } = useWizard();
  switch (step) {
    case STEP_DEMOGRAPHICS:
      return <StepDemographics />;
    case STEP_COMPLAINT:
      return <StepComplaint />;
    case STEP_HISTORY:
      return <StepHistory />;
    case STEP_LIFESTYLE:
      return <StepLifestyle />;
    case STEP_QA:
    case STEP_SUMMARY:
      return <WizardStep />;
    default:
      return null;
  }
}

function WizardShell() {
  const { step } = useWizard();
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-6">
      {step > STEP_LANDING && <Stepper />}
      <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 shadow-xl backdrop-blur">
        <CurrentStep />
      </div>
    </div>
  );
}

function Home() {
  const { step } = useWizard();
  const stepRegionRef = useRef<HTMLDivElement>(null);
  const landingHeadingRef = useRef<HTMLHeadingElement>(null);
  const previousStep = useRef(step);

  // After a step change the control that had focus is gone, so focus falls
  // back to <body> and a screen reader never announces the new screen. Move
  // focus to the step region, or back to the landing heading when the wizard
  // is reset. The first mount is intentionally left alone.
  useEffect(() => {
    if (step === STEP_LANDING) {
      if (previousStep.current !== STEP_LANDING) {
        landingHeadingRef.current?.focus();
      }
    } else {
      stepRegionRef.current?.focus();
    }
    previousStep.current = step;
  }, [step]);

  if (step === STEP_LANDING) {
    return (
      <div className="w-full">
        <Landing headingRef={landingHeadingRef} />
        <FaqSection />
      </div>
    );
  }

  return (
    <div ref={stepRegionRef} tabIndex={-1} className="w-full outline-none">
      <WizardShell />
    </div>
  );
}

function Shell() {
  const { lang } = useI18n();

  // One route. A stale bookmark (e.g. /next/...) must still land on the
  // wizard, so the address bar is rewritten to the root with the query kept —
  // a shared ?lang= link keeps its language.
  useEffect(() => {
    normalizePath();
  }, []);

  return (
    <WizardProvider lang={lang}>
      <div className="flex min-h-screen w-full flex-col items-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <Header />
        <main className="flex w-full flex-1 flex-col items-center pt-4">
          {/* /privacy and /terms are served as static HTML by the Python
              backend (they negotiate ?lang=), so the SPA must not claim them. */}
          <Home />
        </main>
        <Footer />
      </div>
    </WizardProvider>
  );
}

export function App() {
  return (
    <I18nProvider>
      <Shell />
    </I18nProvider>
  );
}
