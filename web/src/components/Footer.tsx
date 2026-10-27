import { useI18n } from "../i18n/I18nProvider";
import { handleHomeLink } from "../navigation";

export function Footer() {
  const { t, lang } = useI18n();

  return (
    <footer className="mx-auto w-full max-w-3xl px-4 py-4">
      <hr className="border-white/10" />
      <p className="mt-3 text-center text-xs text-slate-400">
        {t.footer_disclaimer}
      </p>
      <div className="mt-2 flex items-center justify-center gap-2 text-xs">
        {/* Legal pages are static HTML served by the Python backend; they
            negotiate their language from ?lang= before Accept-Language. */}
        <a
          href={`/privacy?lang=${lang}`}
          className="text-cyan-300 hover:underline"
        >
          {t.footer_privacy}
        </a>
        <span className="text-slate-500">·</span>
        <a href={`/terms?lang=${lang}`} className="text-cyan-300 hover:underline">
          {t.footer_terms}
        </a>
      </div>
      <div className="mt-2 text-center text-[10px] text-slate-600">
        <a href="/" onClick={handleHomeLink}>
          PreConsult
        </a>
      </div>
    </footer>
  );
}
