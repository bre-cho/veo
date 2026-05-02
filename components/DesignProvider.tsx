"use client";

import { createContext, useContext, useMemo, useState } from "react";
import { DesignSystem } from "@/lib/design/schema";
import { parseDesignMd } from "@/lib/design/parser";
import { designToCssVars } from "@/lib/design/css-vars";

const defaultDesignMd = `---
version: alpha
name: "Revenue Ads System"
colors:
  primary: "#0A0F2C"
  accent: "#2563EB"
  highlight: "#FACC15"
  background: "#0A0F2C"
  surface: "#111827"
  text: "#FFFFFF"
typography:
  headline-lg:
    fontFamily: "Inter"
    fontSize: 48px
    fontWeight: 700
rounded:
  md: 8px
  lg: 16px
spacing:
  md: 16px
  lg: 32px
conversion:
  goal: "Lead"
  platform: "TikTok"
  primaryAction: "demo"
---
`;

type Ctx = {
  designMd: string;
  setDesignMd: (v: string) => void;
  design: DesignSystem;
  cssVars: React.CSSProperties;
};

const DesignContext = createContext<Ctx | null>(null);

export function DesignProvider({ children }: { children: React.ReactNode }) {
  const [designMd, setDesignMd] = useState(defaultDesignMd);
  const design = useMemo(() => parseDesignMd(designMd), [designMd]);
  const cssVars = useMemo(() => designToCssVars(design), [design]);

  return (
    <DesignContext.Provider value={{ designMd, setDesignMd, design, cssVars }}>
      <div style={cssVars}>{children}</div>
    </DesignContext.Provider>
  );
}

export function useDesign() {
  const ctx = useContext(DesignContext);
  if (!ctx) throw new Error("useDesign must be used inside DesignProvider");
  return ctx;
}
