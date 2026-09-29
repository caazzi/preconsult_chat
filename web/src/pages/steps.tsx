import { useI18n } from "../i18n/I18nProvider";
import { useWizard } from "../wizard/WizardProvider";
import { ErrorCallout, FormStepLayout } from "../components/FormStepLayout";
import { localizeValue } from "../wizard/payload";

const AGE_BRACKETS = ["18-25", "26-35", "36-45", "46-60", "60+"];
const DURATION_KEYS = ["today", "days", "weeks", "months", "years"];
const CONDITION_KEYS = ["asthma", "depression", "diabetes", "hypertension", "thyroid"];
const FAMILY_KEYS = ["alzheimers", "cancer", "diabetes", "heart"];
const SMOKING_KEYS = ["never", "former", "current"];
const ALCOHOL_KEYS = ["never", "rarely", "socially", "frequently"];

function ChipGrid({
  options,
  value,
  onSelect,
  columns = 5,
}: {
  options: { id: string; label: string }[];
  value: string;
  onSelect: (id: string) => void;
  columns?: 2 | 3 | 4 | 5;
}) {
  const cols: Record<number, string> = {
    2: "grid-cols-2",
    3: "grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-5",
  };
  return (
    <div className={`grid ${cols[columns]} gap-3`}>
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onSelect(opt.id)}
          aria-pressed={value === opt.id}
          className={`min-h-[48px] rounded-lg border px-3 py-2 text-sm transition ${
            value === opt.id
              ? "border-cyan-300 bg-cyan-500/25 text-cyan-100"
              : "border-white/20 text-slate-200 hover:bg-white/5"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function MultiChipGrid({
  options,
  selected,
  onToggle,
  columns = 5,
}: {
  options: { id: string; label: string }[];
  selected: string[];
  onToggle: (id: string) => void;
  columns?: 2 | 4 | 5;
}) {
  const cols: Record<number, string> = {
    2: "grid-cols-2",
    4: "grid-cols-2 sm:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-5",
  };
  return (
    <div className={`grid ${cols[columns]} gap-3`}>
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onToggle(opt.id)}
          aria-pressed={selected.includes(opt.id)}
          className={`min-h-[48px] rounded-lg border px-3 py-2 text-sm transition ${
            selected.includes(opt.id)
              ? "border-cyan-300 bg-cyan-500/25 text-cyan-100"
              : "border-white/20 text-slate-200 hover:bg-white/5"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function StepDemographics() {
  const { t } = useI18n();
  const { data, update, error, clearError, goToComplaint, goBack } = useWizard();
  return (
    <div>
      <ErrorCallout message={error} />
      <FormStepLayout
        title={t.intake}
        description={t.intake_desc}
        onBack={goBack}
        onNext={() => {
          clearError();
          goToComplaint();
        }}
        nextLabel={t.start_btn}
      >
        <div className="space-y-4">
          <div>
            <p className="mb-2 font-bold text-slate-200">{t.age}</p>
            <ChipGrid
              options={AGE_BRACKETS.map((b) => ({ id: b, label: b }))}
              value={data.ageBracket}
              onSelect={(id) => update("ageBracket", id)}
            />
          </div>
          <div>
            <label
              htmlFor="gender"
              className="mb-2 block font-bold text-slate-200"
            >
              {t.gender}
            </label>
            <select
              id="gender"
              aria-label="Select your gender"
              value={data.gender}
              onChange={(e) => update("gender", e.target.value)}
              className="min-h-[48px] w-full rounded-lg border border-white/20 bg-slate-900 px-3 text-slate-100"
            >
              <option value="">{t.gender_ph}</option>
              {t.gender_opts.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
        </div>
      </FormStepLayout>
    </div>
  );
}

export function StepComplaint() {
  const { t } = useI18n();
  const { data, update, error, clearError, goToHistory, goBack } = useWizard();
  return (
    <div>
      <ErrorCallout message={error} />
      <FormStepLayout
        title={t.step_1}
        description={t.step_1_desc}
        onBack={goBack}
        onNext={() => {
          clearError();
          goToHistory();
        }}
        nextLabel={t.start_btn}
      >
        <div className="space-y-4">
          <div>
            <label
              htmlFor="chief"
              className="mb-2 block font-bold text-slate-200"
            >
              {t.concern}
            </label>
            <textarea
              id="chief"
              aria-label="Chief Complaint"
              placeholder={t.concern_ph}
              value={data.chiefComplaint}
              onChange={(e) => {
                update("chiefComplaint", e.target.value);
                update("complaintDetail", "");
              }}
              className="min-h-[80px] w-full rounded-lg border border-white/20 bg-slate-900 p-3 text-slate-100"
            />
          </div>
          <div>
            <p className="mb-2 font-bold text-slate-200">{t.duration}</p>
            <ChipGrid
              options={DURATION_KEYS.map((k) => ({
                id: k,
                label: localizeValue(t, "duration", k),
              }))}
              value={data.duration}
              onSelect={(id) => update("duration", id)}
            />
          </div>
          <div>
            <label
              htmlFor="specialist"
              className="mb-2 block font-bold text-slate-200"
            >
              {t.specialist}
            </label>
            <input
              id="specialist"
              aria-label="Specialist you are seeing"
              placeholder={t.specialist_ph}
              value={data.specialist}
              onChange={(e) => update("specialist", e.target.value)}
              className="min-h-[48px] w-full rounded-lg border border-white/20 bg-slate-900 px-3 text-slate-100"
            />
          </div>
        </div>
      </FormStepLayout>
    </div>
  );
}

export function StepHistory() {
  const { t } = useI18n();
  const {
    data,
    toggle,
    update,
    addMedication,
    updateMedication,
    removeMedication,
    error,
    clearError,
    goToLifestyle,
    goBack,
  } = useWizard();
  return (
    <div>
      <ErrorCallout message={error} />
      <FormStepLayout
        title={t.step_2}
        description={t.step_2_desc}
        onBack={goBack}
        onNext={() => {
          clearError();
          goToLifestyle();
        }}
        nextLabel={t.start_btn}
      >
        <div className="space-y-4">
          <div>
            <p className="mb-2 font-bold text-slate-200">
              {t.conditions_label}
            </p>
            <MultiChipGrid
              options={CONDITION_KEYS.map((k) => ({
                id: k,
                label: localizeValue(t, "conditions", k),
              }))}
              selected={data.conditions}
              onToggle={(id) => toggle("conditions", id)}
            />
            <button
              type="button"
              onClick={() => update("conditions", [])}
              aria-pressed={data.conditions.length === 0}
              className={`mt-3 min-h-[48px] w-full rounded-lg border px-3 py-2 text-sm ${
                data.conditions.length === 0
                  ? "border-cyan-300 bg-cyan-500/25 text-cyan-100"
                  : "border-white/20 text-slate-300 hover:bg-white/5"
              }`}
            >
              {t.conditions_none}
            </button>
          </div>

          <div>
            <p className="mb-2 font-bold text-slate-200">
              {t.medications_label}
            </p>
            <div className="space-y-2">
              {data.medications.map((med, idx) => (
                <div key={idx} className="flex w-full gap-2">
                  <input
                    aria-label="Medication name"
                    placeholder={t.medications_ph}
                    value={med}
                    onChange={(e) => updateMedication(idx, e.target.value)}
                    className="min-h-[48px] flex-1 rounded-lg border border-white/20 bg-slate-900 px-3 text-slate-100"
                  />
                  <button
                    type="button"
                    aria-label="Remove medication"
                    onClick={() => removeMedication(idx)}
                    className="min-h-[48px] rounded-lg border border-red-500/40 px-3 text-red-300 hover:bg-red-500/10"
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addMedication}
              className="mt-2 min-h-[48px] rounded-lg px-3 text-cyan-300 hover:bg-cyan-400/5"
            >
              {t.add_medication}
            </button>
          </div>

          <div>
            <p className="mb-2 font-bold text-slate-200">
              {t.allergies_label}
            </p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { val: false, label: t.allergies_no },
                { val: true, label: t.allergies_yes },
              ].map(({ val, label }) => (
                <button
                  key={label}
                  type="button"
                  aria-pressed={data.allergiesFlag === val}
                  onClick={() => update("allergiesFlag", val)}
                  className={`min-h-[48px] rounded-lg border px-3 py-2 text-sm ${
                    data.allergiesFlag === val
                      ? "border-cyan-300 bg-cyan-500/25 text-cyan-100"
                      : "border-white/20 text-slate-200 hover:bg-white/5"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            {data.allergiesFlag && (
              <textarea
                aria-label="List your drug allergies"
                placeholder={t.allergies_ph}
                value={data.allergiesText}
                onChange={(e) => update("allergiesText", e.target.value)}
                className="mt-2 min-h-[48px] w-full rounded-lg border border-white/20 bg-slate-900 p-3 text-slate-100"
              />
            )}
          </div>
        </div>
      </FormStepLayout>
    </div>
  );
}

export function StepLifestyle() {
  const { t } = useI18n();
  const {
    data,
    update,
    toggle,
    error,
    clearError,
    startSession,
    goBack,
    loading,
  } = useWizard();
  return (
    <div>
      <ErrorCallout message={error} />
      <FormStepLayout
        title={t.step_3}
        description={t.step_3_desc}
        onBack={goBack}
        onNext={() => {
          clearError();
          void startSession();
        }}
        nextLabel={t.generate_qs_btn}
        nextLoading={loading}
      >
        <div className="space-y-4">
          <div>
            <p className="mb-2 font-bold text-slate-200">
              {t.family_history_label}
            </p>
            <MultiChipGrid
              options={FAMILY_KEYS.map((k) => ({
                id: k,
                label: localizeValue(t, "familyHistory", k),
              }))}
              selected={data.familyHistory}
              onToggle={(id) => toggle("familyHistory", id)}
              columns={4}
            />
          </div>
          <div>
            <p className="mb-2 font-bold text-slate-200">{t.smoking_label}</p>
            <ChipGrid
              options={SMOKING_KEYS.map((k) => ({
                id: k,
                label: localizeValue(t, "smoking", k),
              }))}
              value={data.smoking}
              onSelect={(id) => update("smoking", id)}
              columns={3}
            />
          </div>
          <div>
            <p className="mb-2 font-bold text-slate-200">{t.alcohol_label}</p>
            <ChipGrid
              options={ALCOHOL_KEYS.map((k) => ({
                id: k,
                label: localizeValue(t, "alcohol", k),
              }))}
              value={data.alcohol}
              onSelect={(id) => update("alcohol", id)}
              columns={4}
            />
          </div>
        </div>
      </FormStepLayout>
    </div>
  );
}
