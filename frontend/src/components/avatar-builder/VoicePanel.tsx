"use client";

import { useState } from "react";
import { saveAvatarDna } from "@/src/lib/api";

interface Props {
  avatarId: string;
  onSaved?: () => void;
}

export default function VoicePanel({ avatarId, onSaved }: Props) {
  const [languageCode, setLanguageCode] = useState("");
  const [accentCode, setAccentCode] = useState("");
  const [tone, setTone] = useState("");
  const [pitch, setPitch] = useState("");
  const [speed, setSpeed] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await saveAvatarDna({
        avatar_id: avatarId,
        voice: {
          language_code: languageCode,
          accent_code: accentCode,
          tone,
          pitch,
          speed,
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
    { label: "Language Code", value: languageCode, set: setLanguageCode, placeholder: "e.g. en, zh, es" },
    { label: "Accent Code", value: accentCode, set: setAccentCode, placeholder: "e.g. us, gb, au" },
    { label: "Tone", value: tone, set: setTone, placeholder: "e.g. warm, professional, energetic" },
    { label: "Pitch", value: pitch, set: setPitch, placeholder: "e.g. low, medium, high" },
    { label: "Speed", value: speed, set: setSpeed, placeholder: "e.g. slow, normal, fast" },
  ];

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-neutral-100">Voice DNA</h3>

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
      {saved && <p className="text-xs text-green-400">Voice DNA saved ✓</p>}

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
