"use client";

import { useState, useCallback, useEffect } from "react";
import { listAvatars } from "@/src/lib/api";

export function useMarketplaceHook() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [marketCode, setMarketCode] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAvatars({
        market_code: marketCode || undefined,
        role_id: roleFilter || undefined,
        limit: 50,
      });
      setItems(res.items);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [marketCode, roleFilter]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { items, loading, error, marketCode, setMarketCode, roleFilter, setRoleFilter, reload };
}
