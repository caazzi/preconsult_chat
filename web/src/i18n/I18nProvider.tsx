import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  detectLang,
  getTranslations,
  type Lang,
  type Translation,
} from "../contracts/i18n";

type I18nContextValue = {
  lang: Lang;
  t: Translation;
  setLang: (lang: Lang) => void;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function initialLang(): Lang {
  return detectLang(window.location.search, navigator.language);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  // The document ships as lang="en"; correct it on mount for auto-detected
  // languages and keep it in sync afterwards (a11y + correct pronunciation).
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // Mirror the language into ?lang= so a share/bookmark keeps it. URL only —
  // no cookie and no localStorage, to honour the zero-persistence posture.
  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    const url = new URL(window.location.href);
    url.searchParams.set("lang", next);
    window.history.replaceState(window.history.state, "", url);
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({ lang, t: getTranslations(lang), setLang }),
    [lang, setLang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within an I18nProvider");
  return ctx;
}
