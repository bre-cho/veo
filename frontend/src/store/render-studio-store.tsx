"use client";

import React, { createContext, useContext, useReducer } from "react";

interface RenderStudioState {
  avatarId: string | null;
  contentGoal: string;
  marketCode: string;
  conversionMode: string;
}

type RenderStudioAction =
  | { type: "SET_AVATAR"; payload: string | null }
  | { type: "SET_GOAL"; payload: string }
  | { type: "SET_MARKET"; payload: string }
  | { type: "SET_CONVERSION_MODE"; payload: string };

const initialState: RenderStudioState = {
  avatarId: null,
  contentGoal: "",
  marketCode: "",
  conversionMode: "",
};

function renderStudioReducer(
  state: RenderStudioState,
  action: RenderStudioAction
): RenderStudioState {
  switch (action.type) {
    case "SET_AVATAR":
      return { ...state, avatarId: action.payload };
    case "SET_GOAL":
      return { ...state, contentGoal: action.payload };
    case "SET_MARKET":
      return { ...state, marketCode: action.payload };
    case "SET_CONVERSION_MODE":
      return { ...state, conversionMode: action.payload };
    default:
      return state;
  }
}

const RenderStudioContext = createContext<{
  state: RenderStudioState;
  dispatch: React.Dispatch<RenderStudioAction>;
} | null>(null);

export function RenderStudioProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(renderStudioReducer, initialState);
  return (
    <RenderStudioContext.Provider value={{ state, dispatch }}>
      {children}
    </RenderStudioContext.Provider>
  );
}

export function useRenderStudio() {
  const ctx = useContext(RenderStudioContext);
  if (!ctx) throw new Error("useRenderStudio must be used within RenderStudioProvider");
  return ctx;
}
