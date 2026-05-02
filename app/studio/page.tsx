import { DesignProvider } from "@/components/DesignProvider";
import { PromptOptimizerPanel } from "@/components/PromptOptimizerPanel";

export default function StudioPage() {
  return (
    <DesignProvider>
      <PromptOptimizerPanel />
    </DesignProvider>
  );
}
