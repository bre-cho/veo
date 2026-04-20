"use client";

import { useState, useCallback } from "react";
import { recommendTemplate } from "@/src/lib/api";

export function useTemplateFit() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recommend = useCallback(
    async (payload: { avatar_id: string; content_goal: string; limit?: number }) => {
      setLoading(true);
      setError(null);
      try {
        const res = await recommendTemplate(payload);
        setTemplates(res.templates);
        return res;
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { templates, loading, error, recommend };
}
