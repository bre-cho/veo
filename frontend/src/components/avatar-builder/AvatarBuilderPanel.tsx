"use client";

import { useState } from "react";
import IdentityPanel from "./IdentityPanel";
import VisualPanel from "./VisualPanel";
import VoicePanel from "./VoicePanel";
import MotionPanel from "./MotionPanel";
import AvatarPreviewStage from "./AvatarPreviewStage";
import SavePublishBar from "./SavePublishBar";

const STEPS = ["Identity", "Visual", "Voice", "Motion", "Preview"];

interface Props {
  avatarId: string | null;
  onComplete?: (avatarId: string) => void;
}

export default function AvatarBuilderPanel({ avatarId, onComplete }: Props) {
  const [currentStep, setCurrentStep] = useState(0);

  const stepForward = () => setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));

  return (
    <div className="flex flex-col gap-6">
      {/* Step indicator */}
      <div className="flex gap-2">
        {STEPS.map((label, i) => (
          <button
            key={label}
            onClick={() => setCurrentStep(i)}
            className={[
              "flex-1 rounded-xl py-2 text-xs font-semibold transition",
              i === currentStep
                ? "bg-indigo-600 text-white"
                : i < currentStep
                ? "bg-indigo-900/40 text-indigo-300"
                : "bg-neutral-800 text-neutral-500",
            ].join(" ")}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Step content */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
        {!avatarId && currentStep !== 0 && (
          <p className="text-sm text-yellow-400">
            Start by filling in the Identity step first.
          </p>
        )}

        {currentStep === 0 && (
          <IdentityPanel avatarId={avatarId ?? ""} onSaved={stepForward} />
        )}
        {currentStep === 1 && avatarId && (
          <VisualPanel avatarId={avatarId} onSaved={stepForward} />
        )}
        {currentStep === 2 && avatarId && (
          <VoicePanel avatarId={avatarId} onSaved={stepForward} />
        )}
        {currentStep === 3 && avatarId && (
          <MotionPanel avatarId={avatarId} onSaved={stepForward} />
        )}
        {currentStep === 4 && avatarId && (
          <div className="flex flex-col gap-4">
            <AvatarPreviewStage avatarId={avatarId} />
            <SavePublishBar
              avatarId={avatarId}
              onPublished={() => onComplete?.(avatarId)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
