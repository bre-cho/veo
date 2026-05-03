"use client";

import { useEffect, useState } from "react";

type FormState = {
  product_type: string;
  product_info: string;
  goal: string;
  brand: string;
  ratio: string;
};

type Score = {
  attention: number;
  trust: number;
  conversion: number;
  visual: number;
  total: number;
};

type Variant = {
  type: string;
  hook: string;
  offer: string;
  cta: string;
  prompt: string;
  score: Score;
};

type Campaign = {
  id: string;
  industry: string;
  goal: string;
  winner?: { type?: string } | null;
  created_at: string;
};

type WinnerRecord = {
  id: string;
  campaign_id: string;
  type: string;
  hook: string;
  cta: string;
  offer: string;
  prompt: string;
  score: Score;
  created_at: string;
};

type GenerateResult = {
  ok: boolean;
  campaign_id: string;
  industry: string;
  scored_variants: Record<string, Variant>;
  winner: Variant | null;
  next_hints: string[];
};

type DraftPayloadResult = {
  ok: boolean;
  draft?: {
    mode: "draft";
    campaign_id: string;
    source: string;
    generated_at: string;
    platforms: Array<"meta" | "tiktok">;
    payloads: {
      meta: Record<string, unknown> | null;
      tiktok: Record<string, unknown> | null;
    };
    safety: {
      spend_enabled: boolean;
      approval_required: boolean;
      note: string;
    };
  };
};

type AuditLog = {
  id: string;
  campaign_id: string | null;
  action: string;
  platform: string;
  mode: "draft" | "live";
  status: "ok" | "error";
  actor: string;
  request: Record<string, unknown>;
  response: Record<string, unknown> | null;
  created_at: string;
};

const defaultForm: FormState = {
  product_type: "giftset qua tang tri an doanh nghiep cao cap",
  product_info: "hop qua doanh nghiep premium co ribbon, thiep cam on va logo",
  goal: "conversion",
  brand: "Demo Brand",
  ratio: "4:5"
};

export function V6ProDashboard({ enableDeployDraft = true }: { enableDeployDraft?: boolean }) {
  const [form, setForm] = useState<FormState>(defaultForm);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [winners, setWinners] = useState<WinnerRecord[]>([]);
  const [draftPayload, setDraftPayload] = useState<DraftPayloadResult["draft"] | null>(null);
  const [deployingDraft, setDeployingDraft] = useState(false);
  const [approvalToken, setApprovalToken] = useState("");
  const [publishingLive, setPublishingLive] = useState(false);
  const [publishResult, setPublishResult] = useState<Record<string, unknown> | null>(null);
  const [copiedTarget, setCopiedTarget] = useState<"meta" | "tiktok" | "publish" | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditCampaignFilter, setAuditCampaignFilter] = useState("");
  const [auditActionFilter, setAuditActionFilter] = useState("");
  const [auditStatusFilter, setAuditStatusFilter] = useState("");
  const [auditPlatformFilter, setAuditPlatformFilter] = useState("");
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function loadHistory() {
    const [campaignRes, winnerRes] = await Promise.all([
      fetch("/api/v6/campaigns", { cache: "no-store" }),
      fetch("/api/v6/winners", { cache: "no-store" })
    ]);

    const campaignData = await campaignRes.json();
    const winnerData = await winnerRes.json();

    setCampaigns(campaignData.campaigns || []);
    setWinners(winnerData.winners || []);
  }

  async function loadAuditLogs(filters?: {
    campaignId?: string;
    action?: string;
    status?: string;
    platform?: string;
  }) {
    try {
      setLoadingAudit(true);
      const params = new URLSearchParams({ limit: "20" });
      const campaignId = filters?.campaignId?.trim();
      const action = filters?.action?.trim();
      const status = filters?.status?.trim();
      const platform = filters?.platform?.trim();

      if (campaignId) {
        params.set("campaign_id", campaignId);
      }
      if (action) {
        params.set("action", action);
      }
      if (status) {
        params.set("status", status);
      }
      if (platform) {
        params.set("platform", platform);
      }

      const res = await fetch(`/api/v7/audit?${params.toString()}`, { cache: "no-store" });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Cannot load audit logs");
      }

      setAuditLogs(data.logs || []);
    } catch (error: any) {
      setMessage(error.message || "Cannot load audit logs");
    } finally {
      setLoadingAudit(false);
    }
  }

  useEffect(() => {
    void loadHistory();
    void loadAuditLogs();
  }, []);

  async function generate() {
    try {
      setLoading(true);
      setMessage("");
      setDraftPayload(null);
      setPublishResult(null);

      const res = await fetch("/api/v6/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Generate failed");
      }

      setResult(data);
      setMessage("Da tao campaign va luu winner DNA.");
      await loadHistory();
    } catch (error: any) {
      setMessage(error.message || "Generate failed");
    } finally {
      setLoading(false);
    }
  }

  async function deployDraft() {
    if (!result?.winner || !result?.campaign_id) {
      setMessage("Can generate campaign truoc khi tao draft payload.");
      return;
    }

    try {
      setDeployingDraft(true);
      setMessage("");

      const res = await fetch("/api/v7/deploy-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campaign_id: result.campaign_id,
          winner: result.winner,
          goal: form.goal,
          brand: form.brand,
          budget_daily: 300000,
          platforms: ["meta", "tiktok"]
        })
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Create draft payload failed");
      }

      setDraftPayload(data.draft || null);
      setPublishResult(null);
      setMessage("Da tao draft payload cho Meta va TikTok (draft mode). Chua live deploy.");
      await loadAuditLogs({ campaignId: result.campaign_id });
    } catch (error: any) {
      setMessage(error.message || "Create draft payload failed");
    } finally {
      setDeployingDraft(false);
    }
  }

  async function copyPayload(target: "meta" | "tiktok") {
    if (!draftPayload?.payloads[target]) {
      setMessage(`Khong co payload ${target} de copy.`);
      return;
    }

    try {
      await navigator.clipboard.writeText(JSON.stringify(draftPayload.payloads[target], null, 2));
      setCopiedTarget(target);
      setMessage(`Da copy JSON payload ${target}.`);
      window.setTimeout(() => setCopiedTarget((prev) => (prev === target ? null : prev)), 1500);
    } catch {
      setMessage("Khong the copy vao clipboard. Kiem tra quyen clipboard tren trinh duyet.");
    }
  }

  async function copyPublishResult() {
    if (!publishResult) {
      setMessage("Chua co publish result de copy.");
      return;
    }

    try {
      await navigator.clipboard.writeText(JSON.stringify(publishResult, null, 2));
      setCopiedTarget("publish");
      setMessage("Da copy JSON publish result.");
      window.setTimeout(() => setCopiedTarget((prev) => (prev === "publish" ? null : prev)), 1500);
    } catch {
      setMessage("Khong the copy publish result vao clipboard.");
    }
  }

  async function publishLive() {
    if (!result?.campaign_id) {
      setMessage("Can campaign_id truoc khi publish live.");
      return;
    }
    if (!approvalToken.trim()) {
      setMessage("Can nhap approval token de publish live.");
      return;
    }

    try {
      setPublishingLive(true);
      setMessage("");

      const res = await fetch("/api/v7/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approval_token: approvalToken,
          campaign_id: result.campaign_id,
          budget_daily: 300000,
          platforms: ["meta", "tiktok"],
          confirm_live: true
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Live publish failed");
      }

      setPublishResult(data);
      setMessage("Da goi publish live. Kiem tra ket qua tung platform trong block ben duoi.");
      await loadAuditLogs({ campaignId: result.campaign_id });
    } catch (error: any) {
      setMessage(error.message || "Live publish failed");
    } finally {
      setPublishingLive(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#07111F] text-white">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        <div className="overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(250,204,21,0.22),_transparent_28%),linear-gradient(135deg,#0f172a,#111827_55%,#172554)] p-8 shadow-[0_30px_100px_rgba(0,0,0,0.35)]">
          <p className="text-sm font-black uppercase tracking-[0.24em] text-[#FACC15]">V6 Pro Dashboard</p>
          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <h1 className="text-4xl font-black tracking-tight sm:text-5xl">Tự động phát hiện ngành, chấm điểm 3 biến thể, lưu winner DNA.</h1>
              <p className="mt-4 text-base text-slate-300 sm:text-lg">
                Patch pack đã được tích hợp vào App Router hiện tại. Giao diện này gọi trực tiếp các route V6 Pro trong Next.js và tự động fallback về memory nếu chưa cấu hình Supabase service role.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <MetricCard label="Chiến dịch" value={String(campaigns.length)} />
              <MetricCard label="Winner DNA" value={String(winners.length)} />
              <MetricCard label="Mục tiêu" value={form.goal} />
              <MetricCard label="Chế độ" value={process.env.NEXT_PUBLIC_SUPABASE_URL ? "db/memory" : "memory"} />
            </div>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-2xl font-black">Tạo chiến dịch</h2>
              <button
                onClick={generate}
                disabled={loading}
                className="rounded-2xl bg-[#2563EB] px-5 py-3 text-sm font-black text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Đang tạo..." : "Tạo quảng cáo"}
              </button>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <Field label="product_type" value={form.product_type} onChange={(value) => setForm({ ...form, product_type: value })} />
              <Field label="brand" value={form.brand} onChange={(value) => setForm({ ...form, brand: value })} />
              <Field label="goal" value={form.goal} onChange={(value) => setForm({ ...form, goal: value })} />
              <Field label="ratio" value={form.ratio} onChange={(value) => setForm({ ...form, ratio: value })} />
            </div>

            <label className="mt-4 block">
              <span className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-slate-400">product_info</span>
              <textarea
                value={form.product_info}
                onChange={(event) => setForm({ ...form, product_info: event.target.value })}
                className="min-h-32 w-full rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#FACC15]/60"
              />
            </label>

            {message ? <p className="mt-4 text-sm font-semibold text-[#FACC15]">{message}</p> : null}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
            <h2 className="text-2xl font-black">Winner</h2>
            {!result?.winner ? (
              <p className="text-sm text-slate-400">Chưa có kết quả. Hãy tạo một chiến dịch để xem winner.</p>
            ) : (
              <div className="mt-5 space-y-4">
                <div className="inline-flex rounded-full border border-[#FACC15]/30 bg-[#FACC15]/10 px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-[#FACC15]">
                  {result.industry}
                </div>
                <div>
                  <h3 className="text-3xl font-black capitalize">{result.winner.type}</h3>
                  <p className="mt-2 text-slate-300">{result.winner.hook}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <InfoCard label="CTA" value={result.winner.cta} />
                  <InfoCard label="Điểm tổng" value={`${result.winner.score.total}/100`} />
                </div>
                {enableDeployDraft ? (
                  <button
                    onClick={deployDraft}
                    disabled={deployingDraft}
                    className="w-full rounded-2xl border border-[#FACC15]/30 bg-[#FACC15]/20 px-4 py-3 text-sm font-black text-[#FACC15] transition hover:bg-[#FACC15]/30 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {deployingDraft ? "Đang tạo draft payload..." : "Triển khai Draft (Meta + TikTok)"}
                  </button>
                ) : null}
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Prompt</p>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-200">{result.winner.prompt}</p>
                </div>
                {result.next_hints?.length ? (
                  <div className="rounded-3xl border border-[#2563EB]/20 bg-[#2563EB]/10 p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#93C5FD]">Gợi ý tiếp theo</p>
                    <div className="mt-3 space-y-2 text-sm text-slate-200">
                      {result.next_hints.map((hint) => (
                        <p key={hint}>{hint}</p>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </div>

        {result?.scored_variants ? (
          <section className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-2xl font-black">3 biến thể</h2>
              <p className="text-sm text-slate-400">Authority, viral, conversion được chấm điểm trên cùng một bộ quy tắc.</p>
            </div>
            <div className="mt-5 grid gap-4 lg:grid-cols-3">
              {Object.values(result.scored_variants).map((variant) => (
                <article key={variant.type} className="rounded-[24px] border border-white/10 bg-white/[0.04] p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-[#93C5FD]">{variant.type}</p>
                      <h3 className="mt-3 text-3xl font-black">{variant.score.total}/100</h3>
                    </div>
                    <span className="rounded-full bg-[#FACC15] px-3 py-1 text-xs font-black text-slate-900">{variant.offer}</span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-300">{variant.hook}</p>
                  <div className="mt-5 grid grid-cols-2 gap-3 text-sm text-slate-200">
                    <ScorePill label="Chú ý" value={variant.score.attention} />
                    <ScorePill label="Tin cậy" value={variant.score.trust} />
                    <ScorePill label="Chuyển đổi" value={variant.score.conversion} />
                    <ScorePill label="Hình ảnh" value={variant.score.visual} />
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {enableDeployDraft && draftPayload ? (
          <section className="rounded-[28px] border border-[#FACC15]/20 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-2xl font-black">V7 Draft Payload</h2>
              <span className="rounded-full border border-[#FACC15]/30 bg-[#FACC15]/10 px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-[#FACC15]">
                {draftPayload.mode}
              </span>
            </div>
            <p className="mt-3 text-sm text-slate-300">Campaign: {draftPayload.campaign_id}</p>
            <p className="mt-1 text-sm text-slate-400">{draftPayload.safety.note}</p>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#93C5FD]">Schema Meta</p>
                  <button
                    onClick={() => copyPayload("meta")}
                    className="rounded-xl border border-white/20 bg-white/5 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.08em] text-slate-200 hover:bg-white/10"
                  >
                    {copiedTarget === "meta" ? "Đã sao chép" : "Copy JSON"}
                  </button>
                </div>
                <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">
                  {JSON.stringify(draftPayload.payloads.meta, null, 2)}
                </pre>
              </div>

              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#93C5FD]">Schema TikTok</p>
                  <button
                    onClick={() => copyPayload("tiktok")}
                    className="rounded-xl border border-white/20 bg-white/5 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.08em] text-slate-200 hover:bg-white/10"
                  >
                    {copiedTarget === "tiktok" ? "Đã sao chép" : "Copy JSON"}
                  </button>
                </div>
                <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">
                  {JSON.stringify(draftPayload.payloads.tiktok, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-5 rounded-[24px] border border-[#FACC15]/25 bg-[#FACC15]/5 p-4">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#FACC15]">Cổng đăng Live</p>
              <p className="mt-2 text-sm text-slate-300">Bắt buộc nhập approval token + confirm_live=true ở backend để tránh đăng live ngoài ý muốn.</p>
              <p className="mt-2 text-xs text-slate-500">Rotating token: đặt DEPLOY_APPROVAL_TOKEN_SECRET và chạy lệnh npm run token:approval. Token mặc định hết hạn sau 10 phút.</p>

              <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]">
                <input
                  type="password"
                  value={approvalToken}
                  onChange={(event) => setApprovalToken(event.target.value)}
                  placeholder="Nhap approval token static hoac rotating"
                  className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#FACC15]/60"
                />
                <button
                  onClick={publishLive}
                  disabled={publishingLive}
                  className="rounded-2xl bg-[#F97316] px-5 py-3 text-sm font-black text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {publishingLive ? "Đang đăng..." : "Đăng Live"}
                </button>
              </div>

              {publishResult ? (
                <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-300">Kết quả đăng</p>
                    <button
                      onClick={copyPublishResult}
                      className="rounded-xl border border-white/20 bg-white/5 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.08em] text-slate-200 hover:bg-white/10"
                    >
                      {copiedTarget === "publish" ? "Đã sao chép" : "Copy JSON"}
                    </button>
                  </div>
                  <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">
                    {JSON.stringify(publishResult, null, 2)}
                  </pre>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        <section className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-2xl font-black">Nhật ký V7 Audit</h2>
              <p className="mt-2 text-sm text-slate-400">Lọc theo campaign_id, action, status và platform để theo dõi draft, publish và token bị từ chối.</p>
            </div>
            <button
              onClick={() =>
                loadAuditLogs({
                  campaignId: auditCampaignFilter,
                  action: auditActionFilter,
                  status: auditStatusFilter,
                  platform: auditPlatformFilter
                })
              }
              disabled={loadingAudit}
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm font-black text-white hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loadingAudit ? "Đang tải..." : "Làm mới"}
            </button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-[1.2fr_240px_180px_180px_auto]">
            <input
              value={auditCampaignFilter}
              onChange={(event) => setAuditCampaignFilter(event.target.value)}
              placeholder="Lọc theo campaign_id"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#93C5FD]/60"
            />
            <select
              value={auditActionFilter}
              onChange={(event) => setAuditActionFilter(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-[#07111F] px-4 py-3 text-sm text-white outline-none focus:border-[#93C5FD]/60"
            >
              <option value="">Tất cả action</option>
              <option value="draft_created">draft_created</option>
              <option value="publish_attempt">publish_attempt</option>
              <option value="publish_denied">publish_denied</option>
              <option value="publish_failed">publish_failed</option>
            </select>
            <select
              value={auditStatusFilter}
              onChange={(event) => setAuditStatusFilter(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-[#07111F] px-4 py-3 text-sm text-white outline-none focus:border-[#93C5FD]/60"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="ok">ok</option>
              <option value="error">error</option>
            </select>
            <select
              value={auditPlatformFilter}
              onChange={(event) => setAuditPlatformFilter(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-[#07111F] px-4 py-3 text-sm text-white outline-none focus:border-[#93C5FD]/60"
            >
              <option value="">Tất cả nền tảng</option>
              <option value="meta">meta</option>
              <option value="tiktok">tiktok</option>
            </select>
            <button
              onClick={() => {
                setAuditCampaignFilter("");
                setAuditActionFilter("");
                setAuditStatusFilter("");
                setAuditPlatformFilter("");
                void loadAuditLogs();
              }}
              className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm font-black text-white hover:bg-white/[0.08]"
            >
              Đặt lại bộ lọc
            </button>
          </div>

          <div className="mt-5 space-y-3">
            {auditLogs.length ? (
              auditLogs.map((log) => (
                <div key={log.id} className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-[#93C5FD]/30 bg-[#93C5FD]/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.14em] text-[#93C5FD]">{log.action}</span>
                        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] font-black uppercase tracking-[0.14em] text-slate-300">{log.platform}</span>
                        <span className={`rounded-full px-3 py-1 text-[11px] font-black uppercase tracking-[0.14em] ${log.status === "ok" ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"}`}>
                          {log.status}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-300">campaign_id: {log.campaign_id || "-"}</p>
                      <p className="mt-1 text-xs text-slate-500">{new Date(log.created_at).toLocaleString("vi-VN")}</p>
                    </div>
                    <div className="grid gap-3 lg:w-[52%] lg:grid-cols-2">
                      <pre className="max-h-40 overflow-auto rounded-2xl border border-white/10 bg-black/20 p-3 text-xs leading-6 text-slate-300">{JSON.stringify(log.request, null, 2)}</pre>
                      <pre className="max-h-40 overflow-auto rounded-2xl border border-white/10 bg-black/20 p-3 text-xs leading-6 text-slate-300">{JSON.stringify(log.response, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">Chưa có audit log phù hợp bộ lọc hiện tại.</p>
            )}
          </div>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <section className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
            <h2 className="text-2xl font-black">Chiến dịch gần đây</h2>
            <div className="mt-5 space-y-3">
              {campaigns.length ? (
                campaigns.map((campaign) => (
                  <div key={campaign.id} className="grid gap-3 rounded-[22px] border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300 sm:grid-cols-[1fr_1fr_1fr_1.4fr]">
                    <span className="font-semibold text-white">{campaign.industry}</span>
                    <span>{campaign.goal}</span>
                    <span>{campaign.winner?.type || "-"}</span>
                    <span>{new Date(campaign.created_at).toLocaleString("vi-VN")}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400">Chưa có chiến dịch nào.</p>
              )}
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_16px_50px_rgba(0,0,0,0.28)]">
            <h2 className="text-2xl font-black">Winner DNA</h2>
            <div className="mt-5 space-y-3">
              {winners.length ? (
                winners.map((winner) => (
                  <div key={winner.id} className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-full border border-[#93C5FD]/30 bg-[#93C5FD]/10 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-[#93C5FD]">
                        {winner.type}
                      </span>
                      <span className="text-xs text-slate-500">{new Date(winner.created_at).toLocaleString("vi-VN")}</span>
                    </div>
                    <p className="mt-3 font-semibold text-white">{winner.hook}</p>
                    <p className="mt-2 text-sm text-slate-300">CTA: {winner.cta}</p>
                    <p className="mt-2 text-xs text-slate-500">Campaign: {winner.campaign_id}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400">Chưa có winner DNA nào.</p>
              )}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-black/20 px-4 py-3">
      <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-xl font-black text-white">{value}</p>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-slate-400">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#FACC15]/60"
      />
    </label>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-sm leading-6 text-white">{value}</p>
    </div>
  );
}

function ScorePill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-2">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">{label}</p>
      <p className="mt-1 font-black text-white">{value}</p>
    </div>
  );
}