import { Suspense } from "react";
import { DesignProvider } from "@/components/DesignProvider";
import { PromptOptimizerPanel } from "@/components/PromptOptimizerPanel";

export default function StudioPage() {
  return (
    <DesignProvider>
      <Suspense fallback={<div className="p-6 text-sm text-slate-300">Dang tai studio...</div>}>
        <PromptOptimizerPanel />
      </Suspense>
    </DesignProvider>
  );
}
