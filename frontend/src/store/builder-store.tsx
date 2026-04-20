"use client";

import React, { createContext, useContext, useReducer } from "react";

interface BuilderState {
  avatarId: string | null;
  name: string;
  roleId: string;
  nicheCode: string;
  marketCode: string;
  step: number;
  isDirty: boolean;
}

type BuilderAction =
  | { type: "SET_AVATAR_ID"; payload: string }
  | { type: "SET_FIELD"; payload: Partial<Omit<BuilderState, "avatarId" | "step" | "isDirty">> }
  | { type: "SET_STEP"; payload: number }
  | { type: "RESET" };

const initialState: BuilderState = {
  avatarId: null,
  name: "",
  roleId: "",
  nicheCode: "",
  marketCode: "",
  step: 0,
  isDirty: false,
};

function builderReducer(state: BuilderState, action: BuilderAction): BuilderState {
  switch (action.type) {
    case "SET_AVATAR_ID":
      return { ...state, avatarId: action.payload };
    case "SET_FIELD":
      return { ...state, ...action.payload, isDirty: true };
    case "SET_STEP":
      return { ...state, step: action.payload };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

const BuilderContext = createContext<{
  state: BuilderState;
  dispatch: React.Dispatch<BuilderAction>;
} | null>(null);

export function BuilderProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(builderReducer, initialState);
  return (
    <BuilderContext.Provider value={{ state, dispatch }}>
      {children}
    </BuilderContext.Provider>
  );
}

export function useBuilder() {
  const ctx = useContext(BuilderContext);
  if (!ctx) throw new Error("useBuilder must be used within BuilderProvider");
  return ctx;
}
