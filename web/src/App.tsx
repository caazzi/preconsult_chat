import { BrowserRouter, Route, Routes } from "react-router-dom";

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
import { PrivacyPage } from "./pages/PrivacyPage";
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
    case STEP_LANDING:
      return <Landing />;
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
      return <Landing />;
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
  return (
    <>
      <WizardShell />
      {step === STEP_LANDING && <FaqSection />}
    </>
  );
}

function Shell() {
  const { lang } = useI18n();
  return (
    <WizardProvider lang={lang}>
      <div className="flex min-h-screen w-full flex-col items-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <Header />
        <main className="flex w-full flex-1 justify-center pt-4">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/privacy" element={<PrivacyPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </WizardProvider>
  );
}

export function App() {
  return (
    <I18nProvider>
      <BrowserRouter
        basename="/next"
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Shell />
      </BrowserRouter>
    </I18nProvider>
  );
}
