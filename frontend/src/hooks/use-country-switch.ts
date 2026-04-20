"use client";

import { useState } from "react";
import { switchCountry } from "@/src/lib/api";

export function useCountrySwitch() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  async function switchTo(marketCode: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await switchCountry(marketCode);
      setResult(res);
      return res;
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return { switchTo, loading, error, result };
}
