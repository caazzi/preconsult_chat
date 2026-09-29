import { useI18n } from "../i18n/I18nProvider";

export function PrivacyPage() {
  const { t } = useI18n();
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <a href="/" className="text-sm text-cyan-300 hover:underline">
        ← PreConsult
      </a>
      <h1 className="mt-4 text-2xl font-semibold text-cyan-300">
        {t.privacy_title}
      </h1>
      <p className="mt-4 whitespace-pre-line text-slate-300">{t.privacy_text}</p>
    </div>
  );
}
