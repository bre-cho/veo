"use client";

import { useMemo } from "react";

import { useT } from "@/src/i18n/useT";

function statusLabel(status: string, t: (key: string) => string): string {
  if (status === "dry_run") return t("factory.statusDryRun");
  if (status === "blocked_pending_approval") return t("factory.statusBlocked");
  if (status === "approved_publish_ready") return t("factory.statusReady");
  return status || "N/A";
}

export function FactoryPublishPanel({
  run,
  approving,
  publishing,
  onApprove,
  onPublish,
}: {
  run: any;
  approving: boolean;
  publishing: boolean;
  onApprove: () => void;
  onPublish: () => void;
}) {
  const t = useT();
  const stage = run?.stages?.find((s: any) => s.stage_name === "PUBLISH");
  const publish = stage?.output || {};

  const canPublish = useMemo(
    () => publish.status === "approved_publish_ready" || publish.status === "published",
    [publish.status],
  );

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h2 className="text-lg font-semibold">{t("factory.publishTitle")}</h2>
      <p className="mt-2 text-sm text-white/70">status: {statusLabel(publish.status, t)}</p>
      <p className="text-sm text-white/70">requires_approval: {publish.requires_approval ? "true" : "false"}</p>
      <p className="text-sm text-white/70">video_url: {publish.video_url || "N/A"}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onApprove}
          disabled={approving}
          className="rounded-xl border border-white/20 px-3 py-2 text-sm hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {approving ? `${t("common.loading")}...` : t("factory.approvePublish")}
        </button>
        <button
          type="button"
          onClick={onPublish}
          disabled={publishing || !canPublish}
          className="rounded-xl border border-emerald-400/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {publishing ? `${t("common.loading")}...` : t("factory.publishLive")}
        </button>
      </div>
    </section>
  );
}
