/**
 * Server-safe exports for fancall translations.
 *
 * This module exports only JSON resources and constants,
 * avoiding React-specific code that would break SSR.
 */

import en from "./locales/en/fancall.json";
import es from "./locales/es/fancall.json";
import id from "./locales/id/fancall.json";
import ja from "./locales/ja/fancall.json";
import ko from "./locales/ko/fancall.json";
import th from "./locales/th/fancall.json";
import tl from "./locales/tl/fancall.json";
import vi from "./locales/vi/fancall.json";
import zh from "./locales/zh/fancall.json";

/** Fancall namespace */
export const FANCALL_NS = "fancall";

/**
 * Translation resources for the fancall namespace.
 * Use with i18next.addResourceBundle(lang, 'fancall', translations)
 *
 * @example
 * import { fancallTranslations, FANCALL_NS } from 'fancall/locale';
 *
 * // Add to existing i18n instance
 * Object.entries(fancallTranslations).forEach(([lang, resources]) => {
 *   i18n.addResourceBundle(lang, FANCALL_NS, resources);
 * });
 */
export const fancallTranslations = {
  en,
  es,
  id,
  ja,
  ko,
  th,
  tl,
  vi,
  zh,
};
