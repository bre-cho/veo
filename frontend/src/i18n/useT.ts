/**
 * Translation hook – returns the t() function for the active language.
 *
 * Usage:
 *   const t = useT();
 *   <h1>{t("home_title")}</h1>
 */
"use client";

import { useCallback } from "react";
import { useLocale } from "@/src/store/locale-store";
import vi, { type TranslationKey } from "./vi";
import en from "./en";

const DICTIONARIES: Record<string, Record<string, string>> = {
  vi: vi as unknown as Record<string, string>,
  en: en as unknown as Record<string, string>,
};

export function useT() {
  const { state } = useLocale();
  const dict = DICTIONARIES[state.languageCode] ?? DICTIONARIES.vi;

  return useCallback(
    (key: TranslationKey, fallback?: string): string => {
      return dict[key] ?? fallback ?? key;
    },
    [dict],
  );
}
