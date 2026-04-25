"use client";

import { useT } from "@/src/i18n/useT";

interface Props {
  marketCode: string;
}

export default function LanguageLockBanner({ marketCode }: Props) {
  const t = useT();
  if (!marketCode) return null;

  return (
    <div className="flex items-center gap-2 rounded-xl border border-yellow-700/40 bg-yellow-900/20 px-4 py-3">
      <span className="text-base">🔒</span>
      <p className="text-sm text-yellow-300">
        {t("lang_lock_prefix")}{" "}
        <strong className="font-semibold">{marketCode}</strong>. {t("lang_lock_change")}.
      </p>
    </div>
  );
}
