"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/src/components/DashboardShell";
import {
  getAutopilotDashboard,
  getKillSwitch,
  getObservabilityStatus,
  listNotificationDeliveries,
  listNotificationEndpoints,
  updateKillSwitch,
  type AutopilotDashboardResponse,
  type KillSwitchResponse,
  type NotificationDeliveryLogResponse,
  type NotificationEndpointResponse,
  type ObservabilityStatusResponse,
} from "@/src/lib/api";

export default function AutopilotStatusPage() {
  const [status, setStatus] = useState<ObservabilityStatusResponse | null>(null);
  const [dashboard, setDashboard] = useState<AutopilotDashboardResponse | null>(null);
  const [killSwitch, setKillSwitch] = useState<KillSwitchResponse | null>(null);
  const [endpoints, setEndpoints] = useState<NotificationEndpointResponse[]>([]);
  const [deliveries, setDeliveries] = useState<NotificationDeliveryLogResponse[]>([]);
  const [actor, setActor] = useState("ops@local");
  const [reason, setReason] = useState("thay doi thu cong tai control plane");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const [s, d, k, e, logs] = await Promise.all([
      getObservabilityStatus(),
      getAutopilotDashboard(),
      getKillSwitch(),
      listNotificationEndpoints(),
      listNotificationDeliveries(20),
    ]);
    setStatus(s);
    setDashboard(d);
    setKillSwitch(k);
    setEndpoints(e);
    setDeliveries(logs);
  };

  useEffect(() => {
    void load();
  }, []);

  const toggleKillSwitch = async (enabled: boolean) => {
    try {
      setBusy(true);
      const next = await updateKillSwitch({ actor, enabled, reason });
      setKillSwitch(next);
      setMessage(`Da cap nhat kill switch: ${enabled ? "BAT" : "TAT"}`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Khong cap nhat duoc kill switch");
    } finally {
      setBusy(false);
    }
  };

  return (
    <DashboardShell title="Tu dong hoa / Giam sat" description="Trang thai control fabric tu dong, metrics, thong bao va kill switch toan cuc.">
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border p-4" data-testid="autopilot-card-kill-switch">
            <div className="text-sm text-gray-500">Kill switch</div>
            <div className="mt-2 text-2xl font-semibold">{killSwitch?.enabled ? "BAT" : "TAT"}</div>
            <div className="mt-2 text-xs text-gray-500">{killSwitch?.reason || "Khong co khoa dang kich hoat"}</div>
          </div>
          <div className="rounded-2xl border p-4" data-testid="autopilot-card-release-gate">
            <div className="text-sm text-gray-500">Cong release</div>
            <div className="mt-2 text-2xl font-semibold">{status?.release_gate_blocked ? "BI CHAN" : "MO"}</div>
          </div>
          <div className="rounded-2xl border p-4" data-testid="autopilot-card-provider-overrides">
            <div className="text-sm text-gray-500">So override provider</div>
            <div className="mt-2 text-2xl font-semibold">{status?.active_provider_overrides ?? 0}</div>
          </div>
          <div className="rounded-2xl border p-4" data-testid="autopilot-card-notification-failures">
            <div className="text-sm text-gray-500">Thong bao loi 24h</div>
            <div className="mt-2 text-2xl font-semibold">{status?.notification_failures_last_24h ?? 0}</div>
          </div>
        </section>

        <section className="rounded-2xl border p-4" data-testid="autopilot-kill-switch-panel">
          <div className="mb-3 text-lg font-semibold">Kill switch toan cuc</div>
          <div className="grid gap-3 md:grid-cols-3">
            <input className="rounded-xl border px-3 py-2" value={actor} onChange={(e) => setActor(e.target.value)} placeholder="nguoi thao tac" data-testid="autopilot-actor-input" />
            <input className="rounded-xl border px-3 py-2" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="ly do" data-testid="autopilot-reason-input" />
            <div className="flex gap-2">
              <button className="rounded-xl border px-4 py-2" onClick={() => toggleKillSwitch(true)} disabled={busy} data-testid="autopilot-enable-kill-switch">Bat</button>
              <button className="rounded-xl border px-4 py-2" onClick={() => toggleKillSwitch(false)} disabled={busy} data-testid="autopilot-disable-kill-switch">Tat</button>
            </div>
          </div>
          {message ? <div className="mt-3 text-sm text-gray-600">{message}</div> : null}
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border p-4" data-testid="autopilot-state-panel">
            <div className="mb-3 text-lg font-semibold">Trang thai tu dong hoa</div>
            <div className="space-y-2 text-sm">
              {dashboard ? Object.entries(dashboard.autopilot_states).map(([key, value]) => (
                <div key={key} className="flex justify-between border-b pb-1">
                  <span>{key}</span>
                  <span>{value}</span>
                </div>
              )) : <div>Dang tai...</div>}
            </div>
            <div className="mt-3 text-xs text-gray-500">Lan chay cuoi: {status?.autopilot_last_execution_at || "khong co"}</div>
          </div>

          <div className="rounded-2xl border p-4" data-testid="autopilot-worker-panel">
            <div className="mb-3 text-lg font-semibold">Dieu khien runtime</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span>Gioi han batch dispatch</span><span>{dashboard?.worker_dispatch_batch_limit ?? "khong co"}</span></div>
              <div className="flex justify-between"><span>So giay dem nguoc poll</span><span>{dashboard?.worker_poll_countdown_seconds ?? "khong co"}</span></div>
              <div className="flex justify-between"><span>So endpoint thong bao</span><span>{endpoints.length}</span></div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border p-4" data-testid="autopilot-audit-panel">
            <div className="mb-3 text-lg font-semibold">Kiem toan quyet dinh gan nhat</div>
            <div className="space-y-2 text-sm">
              {dashboard?.latest_decision_audits?.map((row, idx) => (
                <div key={idx} className="rounded-xl border p-2">
                  <div className="font-medium">{String(row.decision_type)} — {String(row.execution_status)}</div>
                  <div className="text-xs text-gray-500">{String(row.created_at || "")}</div>
                  <div className="text-xs">{String(row.reason || "")}</div>
                </div>
              )) || <div>Dang tai...</div>}
            </div>
          </div>

          <div className="rounded-2xl border p-4" data-testid="autopilot-notification-panel">
            <div className="mb-3 text-lg font-semibold">Lich su giao thong bao gan nhat</div>
            <div className="space-y-2 text-sm">
              {deliveries.map((row) => (
                <div key={row.id} className="rounded-xl border p-2">
                  <div className="font-medium">{row.event_type} → {row.endpoint_name}</div>
                  <div className="text-xs text-gray-500">{row.delivery_status} / {row.channel_type}</div>
                  {row.error_message ? <div className="text-xs text-red-600">{row.error_message}</div> : null}
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}
