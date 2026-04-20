"use client";

import { useState } from "react";
import { saveAvatarDna } from "@/src/lib/api";

interface Props {
  avatarId: string;
  onSaved?: () => void;
}

export default function MotionPanel({ avatarId, onSaved }: Props) {
  const [motionStyle, setMotionStyle] = useState("");
  const [gestureSet, setGestureSet] = useState("");
  const [idleAnimation, setIdleAnimation] = useState("");
  const [lipsyncMode, setLipsyncMode] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await saveAvatarDna({
        avatar_id: avatarId,
        motion: {
          motion_style: motionStyle,
          gesture_set: gestureSet,
          idle_animation: idleAnimation,
          lipsync_mode: lipsyncMode,
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
    { label: "Motion Style", value: motionStyle, set: setMotionStyle, placeholder: "e.g. static, dynamic, subtle" },
    { label: "Gesture Set", value: gestureSet, set: setGestureSet, placeholder: "e.g. minimal, expressive" },
    { label: "Idle Animation", value: idleAnimation, set: setIdleAnimation, placeholder: "e.g. breathe, sway" },
    { label: "Lipsync Mode", value: lipsyncMode, set: setLipsyncMode, placeholder: "e.g. auto, manual" },
  ];

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-neutral-100">Motion DNA</h3>

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
      {saved && <p className="text-xs text-green-400">Motion DNA saved ✓</p>}

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
