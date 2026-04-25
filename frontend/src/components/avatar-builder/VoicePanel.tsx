"use client";

import { useState } from "react";
import { saveAvatarDna } from "@/src/lib/api";
import { useT } from "@/src/i18n/useT";

interface Props {
  avatarId: string;
  onSaved?: () => void;
}

export default function VoicePanel({ avatarId, onSaved }: Props) {
  const t = useT();
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
    { label: t("voice_language_code"), value: languageCode, set: setLanguageCode, placeholder: t("voice_language_placeholder") },
    { label: t("voice_accent_code"), value: accentCode, set: setAccentCode, placeholder: t("voice_accent_placeholder") },
    { label: t("voice_tone"), value: tone, set: setTone, placeholder: t("voice_tone_placeholder") },
    { label: t("voice_pitch"), value: pitch, set: setPitch, placeholder: t("voice_pitch_placeholder") },
    { label: t("voice_speed"), value: speed, set: setSpeed, placeholder: t("voice_speed_placeholder") },
  ];

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-neutral-100">{t("voice_dna_title")}</h3>

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
      {saved && <p className="text-xs text-green-400">{t("voice_dna_saved")}</p>}

      <button
        onClick={handleSave}
        disabled={saving}
        className="self-start rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
      >
        {saving ? t("voice_saving") : t("voice_save_continue")}
      </button>
    </div>
  );
}

