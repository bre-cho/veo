"use client";

import { useState, useEffect } from "react";
import { getAvatar } from "@/src/lib/api";

export function useAvatarPreview(id: string | null) {
  const [avatar, setAvatar] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getAvatar(id)
      .then(setAvatar)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  return { avatar, loading, error };
}
