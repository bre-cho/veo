"use client";

import { useEffect, useState } from "react";
import { getMetaMarketProfiles } from "@/src/lib/api";

interface Props {
  value: string;
  onChange: (code: string) => void;
  label?: string;
}

export default function CountryDropdown({ value, onChange, label }: Props) {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getMetaMarketProfiles()
      .then(setProfiles)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <label className="flex flex-col gap-1">
      {label && <span className="text-xs text-neutral-400">{label}</span>}
      <select
        className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500 disabled:opacity-50"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
      >
        <option value="">
          {loading ? "Dang tai thi truong..." : "Select market"}
        </option>
        {profiles.map((p) => (
          <option key={p.market_code} value={p.market_code}>
            {p.country_name} ({p.market_code})
          </option>
        ))}
      </select>
    </label>
  );
}
