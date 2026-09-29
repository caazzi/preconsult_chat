import { Link } from "react-router-dom";

import { useI18n } from "../i18n/I18nProvider";

export function Header() {
  const { lang, t, setLang } = useI18n();

  return (
    <header className="flex w-full items-center justify-between border-b border-white/10 px-4 py-2 sm:px-6 sm:py-3">
      <Link
        to="/"
        className="text-lg font-semibold text-cyan-300 sm:text-xl"
      >
        {t.title}
      </Link>
      <div className="flex items-center gap-2">
        <label className="sr-only" htmlFor="lang-select">
          {t.lang_select_sr}
        </label>
        <select
          id="lang-select"
          aria-label="Select language"
          value={lang}
          onChange={(e) => setLang(e.target.value as "en" | "pt")}
          className="min-h-[44px] rounded-md bg-transparent px-2 text-sm text-slate-200 outline-none"
        >
          {t.lang_opts.map((code) => (
            <option key={code} value={code} className="bg-slate-900">
              {code}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
