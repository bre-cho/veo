"use client";

import React, { createContext, useContext, useReducer } from "react";

interface LocaleState {
  marketCode: string;
  languageCode: string;
  rtl: boolean;
}

type LocaleAction =
  | { type: "SET_MARKET"; payload: { marketCode: string } }
  | { type: "SET_LANGUAGE"; payload: { languageCode: string; rtl?: boolean } };

const initialState: LocaleState = {
  marketCode: "VN",
  languageCode: "vi",
  rtl: false,
};

function localeReducer(state: LocaleState, action: LocaleAction): LocaleState {
  switch (action.type) {
    case "SET_MARKET":
      return { ...state, marketCode: action.payload.marketCode };
    case "SET_LANGUAGE":
      return {
        ...state,
        languageCode: action.payload.languageCode,
        rtl: action.payload.rtl ?? state.rtl,
      };
    default:
      return state;
  }
}

const LocaleContext = createContext<{
  state: LocaleState;
  dispatch: React.Dispatch<LocaleAction>;
} | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(localeReducer, initialState);
  return (
    <LocaleContext.Provider value={{ state, dispatch }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}
