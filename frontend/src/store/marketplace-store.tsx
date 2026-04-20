"use client";

import React, { createContext, useContext, useReducer } from "react";

interface MarketplaceState {
  marketCode: string;
  roleFilter: string;
  search: string;
  items: any[];
  loading: boolean;
}

type MarketplaceAction =
  | { type: "SET_FILTER"; payload: Partial<Pick<MarketplaceState, "marketCode" | "roleFilter" | "search">> }
  | { type: "SET_ITEMS"; payload: any[] }
  | { type: "SET_LOADING"; payload: boolean };

const initialState: MarketplaceState = {
  marketCode: "",
  roleFilter: "",
  search: "",
  items: [],
  loading: false,
};

function marketplaceReducer(state: MarketplaceState, action: MarketplaceAction): MarketplaceState {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, ...action.payload };
    case "SET_ITEMS":
      return { ...state, items: action.payload };
    case "SET_LOADING":
      return { ...state, loading: action.payload };
    default:
      return state;
  }
}

const MarketplaceContext = createContext<{
  state: MarketplaceState;
  dispatch: React.Dispatch<MarketplaceAction>;
} | null>(null);

export function MarketplaceProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(marketplaceReducer, initialState);
  return (
    <MarketplaceContext.Provider value={{ state, dispatch }}>
      {children}
    </MarketplaceContext.Provider>
  );
}

export function useMarketplace() {
  const ctx = useContext(MarketplaceContext);
  if (!ctx) throw new Error("useMarketplace must be used within MarketplaceProvider");
  return ctx;
}
