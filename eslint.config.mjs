import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["extension/lib/**"] },
  js.configs.recommended,
  {
    files: ["extension/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser, ...globals.webextensions, vis: "readonly" },
    },
    rules: {
      // Bloquea las formas de ejecutar texto como código.
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-unused-vars": ["warn", { args: "none", caughtErrors: "none" }],
    },
  },
  {
    // export.js se carga como script clásico (no módulo).
    files: ["extension/js/export.js", "extension/background.js"],
    languageOptions: { sourceType: "script" },
  },
];
