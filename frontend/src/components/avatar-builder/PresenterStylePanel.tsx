"use client";

import { useState } from "react";
import { saveAvatarDna } from "@/src/lib/api";

interface Props {
  avatarId: string;
  onSaved?: () => void;
}

const PRESETS: Record<
  string,
  { visual: object; motion: object }
> = {
  Professional: {
    visual: { outfit_code: "business", background_code: "studio", age_range: "30-45" },
    motion: { motion_style: "subtle", gesture_set: "minimal", lipsync_mode: "auto" },
  },
  Casual: {
    visual: { outfit_code: "casual", background_code: "outdoor", age_range: "20-35" },
    motion: { motion_style: "dynamic", gesture_set: "expressive", lipsync_mode: "auto" },
  },
  Educational: {
    visual: { outfit_code: "smart_casual", background_code: "classroom", age_range: "25-50" },
    motion: { motion_style: "static", gesture_set: "pointing", lipsync_mode: "auto" },
  },
  Energetic: {
    visual: { outfit_code: "sporty", background_code: "gradient", age_range: "18-30" },
    motion: { motion_style: "dynamic", gesture_set: "enthusiastic", lipsync_mode: "auto" },
  },
};

export default function PresenterStylePanel({ avatarId, onSaved }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function applyPreset(presetName: string) {
    setSelected(presetName);
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const preset = PRESETS[presetName];
      await saveAvatarDna({
        avatar_id: avatarId,
        visual: preset.visual,
        motion: preset.motion,
      });
      setSaved(true);
      onSaved?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-neutral-100">Presenter Style</h3>
      <p className="text-xs text-neutral-400">
        Choose a preset to auto-configure visual and motion DNA.
      </p>

      <div className="grid grid-cols-2 gap-3">
        {Object.keys(PRESETS).map((name) => (
          <button
            key={name}
            onClick={() => applyPreset(name)}
            disabled={saving}
            className={[
              "rounded-xl border px-4 py-3 text-sm font-semibold transition",
              selected === name
                ? "border-indigo-500 bg-indigo-600 text-white"
                : "border-neutral-700 bg-neutral-800 text-neutral-300 hover:border-indigo-500",
            ].join(" ")}
          >
            {name}
          </button>
        ))}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}
      {saved && <p className="text-xs text-green-400">Preset "{selected}" applied ✓</p>}
    </div>
  );
}
