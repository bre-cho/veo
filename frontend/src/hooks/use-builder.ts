"use client";

import { useState, useCallback } from "react";
import { startAvatarBuilder, saveAvatarDna, publishAvatar } from "@/src/lib/api";

export function useBuilderHook() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [avatarId, setAvatarId] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  const start = useCallback(
    async (payload: { name: string; role_id?: string; niche_code?: string; market_code?: string }) => {
      setLoading(true);
      setError(null);
      try {
        const res = await startAvatarBuilder(payload);
        setAvatarId(res.avatar_id);
        return res;
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const save = useCallback(
    async (dna: { visual?: object; voice?: object; motion?: object }) => {
      if (!avatarId) return;
      setLoading(true);
      setError(null);
      try {
        return await saveAvatarDna({ avatar_id: avatarId, ...dna });
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    },
    [avatarId]
  );

  const publish = useCallback(async () => {
    if (!avatarId) return;
    setLoading(true);
    setError(null);
    try {
      return await publishAvatar(avatarId);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [avatarId]);

  return { start, save, publish, loading, error, avatarId, step, setStep };
}
