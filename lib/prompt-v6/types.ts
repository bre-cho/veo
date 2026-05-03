export type V6Goal = "sale" | "lead" | "click" | "brand" | "education" | "event";

export type SellingMechanism =
  | "product"
  | "emotion"
  | "problem"
  | "result"
  | "authority"
  | "offer"
  | "education"
  | "event";

export type V6Input = {
  text: string;
  product?: string;
  industry?: string;
  audience?: string;
  goal?: V6Goal;
  mood?: "luxury" | "bold" | "minimal" | "trust" | "viral";
  hasPackaging?: boolean;
  hasCollection?: boolean;
};

export type V6Output = {
  mechanism: SellingMechanism;
  hook: string;
  cta: string;
  layout: string;
  visual: string;
  posterPrompts: {
    trust: string;
    viral: string;
    conversion: string;
  };
  funnel: any;
  botFlow: string[];
  adsPlan: any;
  kpiRules: any;
};
