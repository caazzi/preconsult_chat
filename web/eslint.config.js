import js from "@eslint/js";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "src/contracts/generated"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    languageOptions: {
      globals: { ...globals.browser },
    },
    rules: {
      // Zero-PHI: the intake draft must never be persisted client-side. Any
      // browser storage API could outlive the tab and contradict the
      // zero-retention promise, so ban them outright (see AGENTS.md).
      "no-restricted-globals": [
        "error",
        {
          name: "localStorage",
          message: "PHI must never be persisted client-side (zero-retention).",
        },
        {
          name: "sessionStorage",
          message: "PHI must never be persisted client-side (zero-retention).",
        },
      ],
    },
  },
);
