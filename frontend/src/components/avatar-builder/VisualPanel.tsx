"use client";

import { useState } from "react";
import { saveAvatarDna } from "@/src/lib/api";

interface Props {
  avatarId: string;
  onSaved?: () => void;
}

export default function VisualPanel({ avatarId, onSaved }: Props) {
  const [skinTone, setSkinTone] = useState("");
  const [hairStyle, setHairStyle] = useState("");
  const [outfitCode, setOutfitCode] = useState("");
  const [backgroundCode, setBackgroundCode] = useState("");
  const [ageRange, setAgeRange] = useState("");
  const [genderExpression, setGenderExpression] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await saveAvatarDna({
        avatar_id: avatarId,
        visual: {
          skin_tone: skinTone,
          hair_style: hairStyle,
          outfit_code: outfitCode,
          background_code: backgroundCode,
          age_range: ageRange,
          gender_expression: genderExpression,
        },
      });
      setSaved(true);
      onSaved?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  const fields: { label: string; value: string; set: (v: string) => void; placeholder: string }[] = [
    { label: "Skin Tone", value: skinTone, set: setSkinTone, placeholder: "e.g. light, medium, dark" },
    { label: "Hair Style", value: hairStyle, set: setHairStyle, placeholder: "e.g. short, wavy, bun" },
    { label: "Outfit Code", value: outfitCode, set: setOutfitCode, placeholder: "e.g. casual, business" },
    { label: "Background Code", value: backgroundCode, set: setBackgroundCode, placeholder: "e.g. studio, outdoor" },
    { label: "Age Range", value: ageRange, set: setAgeRange, placeholder: "e.g. 20-30, 30-40" },
    { label: "Gender Expression", value: genderExpression, set: setGenderExpression, placeholder: "e.g. feminine, masculine, neutral" },
  ];

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-neutral-100">Visual DNA</h3>

      {fields.map((f) => (
        <label key={f.label} className="flex flex-col gap-1">
          <span className="text-xs text-neutral-400">{f.label}</span>
          <input
            className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
            value={f.value}
            onChange={(e) => f.set(e.target.value)}
            placeholder={f.placeholder}
          />
        </label>
      ))}

      {error && <p className="text-xs text-red-400">{error}</p>}
      {saved && <p className="text-xs text-green-400">Visual DNA saved ✓</p>}

      <button
        onClick={handleSave}
        disabled={saving}
        className="self-start rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save & Continue"}
      </button>
    </div>
  );
}
