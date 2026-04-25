"use client";

import { useEffect, useState } from "react";
import {
  GoogleAccount,
  AiEngineConfig,
  listGoogleAccounts,
  createGoogleAccount,
  updateGoogleAccount,
  deleteGoogleAccount,
  getAiEngineConfig,
  saveAiEngineConfig,
  testOpenRouterKey,
} from "@/src/lib/api";
import { useT } from "@/src/i18n/useT";

// ─── Blank form ──────────────────────────────────────────────────────────────

const EMPTY_FORM = {
  label: "",
  gemini_api_key: "",
  google_cloud_project: "",
  google_cloud_location: "global",
  gcs_output_uri: "",
  use_vertex: false,
  rotation_enabled: true,
  is_active: true,
};

type FormState = typeof EMPTY_FORM;

// ─── Page ────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const t = useT();
  const [tab, setTab] = useState<"accounts" | "ai_engine">("accounts");
  const [accounts, setAccounts] = useState<GoogleAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const res = await listGoogleAccounts();
      setAccounts(res.items);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      await createGoogleAccount({
        label: form.label,
        gemini_api_key: form.gemini_api_key || undefined,
        google_cloud_project: form.google_cloud_project || undefined,
        google_cloud_location: form.google_cloud_location || "global",
        gcs_output_uri: form.gcs_output_uri || undefined,
        use_vertex: form.use_vertex,
        rotation_enabled: form.rotation_enabled,
        is_active: form.is_active,
      });
      setForm(EMPTY_FORM);
      setShowAddForm(false);
      await reload();
    } catch (e) {
      setSaveError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function toggleField(account: GoogleAccount, field: "is_active" | "rotation_enabled") {
    try {
      const updated = await updateGoogleAccount(account.id, {
        [field]: !account[field],
      });
      setAccounts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    } catch (e) {
      alert(String(e));
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Xoá tài khoản này?")) return;
    setDeletingId(id);
    try {
      await deleteGoogleAccount(id);
      setAccounts((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      alert(String(e));
    } finally {
      setDeletingId(null);
    }
  }

  const activeCount = accounts.filter((a) => a.is_active && a.rotation_enabled).length;

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 p-8">
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold">{t("settings_title")}</h1>
          <p className="text-neutral-400 mt-1">Quản lý tài khoản Google AI và cài đặt hệ thống.</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-neutral-800 pb-0">
          <button
            onClick={() => setTab("accounts")}
            className={[
              "px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition",
              tab === "accounts"
                ? "border-white text-white"
                : "border-transparent text-neutral-400 hover:text-white",
            ].join(" ")}
          >
            {t("settings_tab_accounts")}
          </button>
          <button
            onClick={() => setTab("ai_engine")}
            className={[
              "px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition",
              tab === "ai_engine"
                ? "border-white text-white"
                : "border-transparent text-neutral-400 hover:text-white",
            ].join(" ")}
          >
            {t("settings_tab_ai_engine")}
          </button>
        </div>

        {/* Accounts Tab */}
        {tab === "accounts" && (
          <div className="space-y-4">

            {/* Summary bar */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="text-sm text-neutral-400">
                {activeCount > 0 ? (
                  <span className="text-green-400 font-medium">
                    ✓ {activeCount} tài khoản đang bật rotation
                  </span>
                ) : (
                  <span className="text-yellow-400">
                    ⚠ Chưa có tài khoản nào bật Account Rotation — hệ thống dùng credentials mặc định từ env.
                  </span>
                )}
              </div>
              <button
                onClick={() => { setShowAddForm((v) => !v); setSaveError(null); }}
                className="rounded-xl bg-white text-black px-4 py-2 text-sm font-semibold hover:bg-neutral-200 transition"
              >
                {showAddForm ? "Huỷ" : "+ Thêm tài khoản"}
              </button>
            </div>

            {/* Add form */}
            {showAddForm && (
              <form
                onSubmit={handleAdd}
                className="rounded-2xl border border-neutral-700 bg-neutral-900 p-5 space-y-4"
              >
                <h2 className="text-base font-semibold">Thêm tài khoản Google AI</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Field label="Tên hiển thị *">
                    <input
                      required
                      value={form.label}
                      onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
                      placeholder="Ví dụ: Account 1 - Project ABC"
                      className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </Field>

                  <Field label="Gemini API Key">
                    <input
                      type="password"
                      value={form.gemini_api_key}
                      onChange={(e) => setForm((f) => ({ ...f, gemini_api_key: e.target.value }))}
                      placeholder="AIzaSy..."
                      className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </Field>

                  <Field label="GCP Project ID">
                    <input
                      value={form.google_cloud_project}
                      onChange={(e) => setForm((f) => ({ ...f, google_cloud_project: e.target.value }))}
                      placeholder="my-gcp-project-123"
                      className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </Field>

                  <Field label="GCP Location">
                    <input
                      value={form.google_cloud_location}
                      onChange={(e) => setForm((f) => ({ ...f, google_cloud_location: e.target.value }))}
                      placeholder="global"
                      className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </Field>

                  <Field label="GCS Output URI">
                    <input
                      value={form.gcs_output_uri}
                      onChange={(e) => setForm((f) => ({ ...f, gcs_output_uri: e.target.value }))}
                      placeholder="gs://my-bucket/outputs/"
                      className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </Field>
                </div>

                <div className="flex flex-wrap gap-4 text-sm">
                  <Toggle
                    label="Dùng Vertex AI"
                    checked={form.use_vertex}
                    onChange={(v) => setForm((f) => ({ ...f, use_vertex: v }))}
                  />
                  <Toggle
                    label="Bật Account Rotation"
                    checked={form.rotation_enabled}
                    onChange={(v) => setForm((f) => ({ ...f, rotation_enabled: v }))}
                  />
                  <Toggle
                    label="Kích hoạt"
                    checked={form.is_active}
                    onChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
                  />
                </div>

                {saveError && (
                  <p className="text-red-400 text-sm">{saveError}</p>
                )}

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={saving}
                    className="rounded-xl bg-white text-black px-5 py-2 text-sm font-semibold hover:bg-neutral-200 transition disabled:opacity-50"
                  >
                    {saving ? "Đang lưu..." : "Lưu tài khoản"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowAddForm(false); setForm(EMPTY_FORM); setSaveError(null); }}
                    className="rounded-xl border border-neutral-700 px-5 py-2 text-sm hover:border-neutral-500 transition"
                  >
                    Huỷ
                  </button>
                </div>
              </form>
            )}

            {/* Account list */}
            {loading ? (
              <p className="text-neutral-500 text-sm">Đang tải...</p>
            ) : error ? (
              <div className="rounded-2xl border border-red-800 bg-red-950/30 p-4 text-sm text-red-300">{error}</div>
            ) : accounts.length === 0 ? (
              <div className="rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8 text-center text-neutral-500 text-sm">
                Chưa có tài khoản nào. Bấm &quot;+ Thêm tài khoản&quot; để bắt đầu.
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <AccountCard
                    key={account.id}
                    account={account}
                    onToggleActive={() => toggleField(account, "is_active")}
                    onToggleRotation={() => toggleField(account, "rotation_enabled")}
                    onDelete={() => handleDelete(account.id)}
                    deleting={deletingId === account.id}
                  />
                ))}
              </div>
            )}

            {/* Usage notes */}
            <div className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-4 text-sm text-neutral-400 space-y-1">
              <p className="font-medium text-neutral-300">Cách hoạt động của Account Rotation:</p>
              <p>• Khi có nhiều tài khoản được bật, hệ thống tự động phân phối jobs theo vòng tròn (round-robin).</p>
              <p>• Tài khoản nào được dùng lâu nhất sẽ được chọn tiếp theo, giúp cân bằng quota.</p>
              <p>• Nếu không có tài khoản nào bật rotation, hệ thống dùng credentials từ biến môi trường.</p>
            </div>

          </div>
        )}

        {/* AI Engine Tab */}
        {tab === "ai_engine" && <AiEngineTab />}

      </div>
    </main>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

// ─── AI Engine Tab ───────────────────────────────────────────────────────────

function AiEngineTab() {
  const t = useT();
  const [config, setConfig] = useState<AiEngineConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [keyInput, setKeyInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"ok" | "fail" | null>(null);
  const [testDetail, setTestDetail] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const c = await getAiEngineConfig();
      setConfig(c);
    } catch {
      /* ignore — API may not be ready yet */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    setSaveError(null);
    setTestResult(null);
    try {
      const updated = await saveAiEngineConfig({
        openrouter_api_key: keyInput || undefined,
      });
      setConfig(updated);
      setKeyInput("");
      setSaveMsg("✓ Đã lưu. Tải lại trang để áp dụng.");
    } catch (err) {
      setSaveError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    const keyToTest = keyInput.trim() || "";
    if (!keyToTest) {
      setTestResult("fail");
      setTestDetail("Nhập OpenRouter API Key trước khi test.");
      return;
    }
    setTesting(true);
    setTestResult(null);
    setTestDetail(null);
    try {
      await testOpenRouterKey(keyToTest);
      setTestResult("ok");
    } catch (err) {
      setTestResult("fail");
      setTestDetail(String(err).replace(/^Error:\s*/, ""));
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return <p className="text-neutral-500 text-sm">Đang tải...</p>;
  }

  return (
    <div className="space-y-6">
      {/* Info */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-4 text-sm text-neutral-400 space-y-1">
        <p className="font-medium text-neutral-300">OpenRouter API Key</p>
        <p>
          OpenRouter cung cấp quyền truy cập vào nhiều mô hình AI (GPT-4o, Claude, Gemini…)
          để hỗ trợ tính năng tạo script và cải thiện nội dung.
        </p>
        <p>
          Lấy key tại{" "}
          <a
            href="https://openrouter.ai/keys"
            target="_blank"
            rel="noreferrer"
            className="text-blue-400 hover:underline"
          >
            openrouter.ai/keys
          </a>
          {" "}→ Create Key → đặt tên <em>KOL Studio</em>.
        </p>
      </div>

      {/* Current status */}
      {config && (
        <div className="flex items-center gap-2 text-sm">
          <span
            className={[
              "inline-block h-2 w-2 rounded-full",
              config.has_openrouter_api_key ? "bg-green-400" : "bg-neutral-600",
            ].join(" ")}
          />
          {config.has_openrouter_api_key ? (
            <span className="text-green-400">
              Key đang hoạt động:{" "}
              <code className="text-neutral-300">{config.openrouter_api_key_masked}</code>
            </span>
          ) : (
            <span className="text-yellow-400">Chưa có API Key. Nhập và lưu bên dưới.</span>
          )}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSave} className="rounded-2xl border border-neutral-700 bg-neutral-900 p-5 space-y-4">
        <h2 className="text-base font-semibold">Cập nhật OpenRouter API Key</h2>

        <Field label="OpenRouter API Key">
          <input
            type="password"
            value={keyInput}
            onChange={(e) => {
              setKeyInput(e.target.value);
              setTestResult(null);
            }}
            placeholder="sk-or-v1-..."
            className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm font-mono focus:outline-none focus:border-neutral-500"
          />
        </Field>

        {/* Test result */}
        {testResult === "ok" && (
          <p className="text-green-400 text-sm">✓ Key hợp lệ — sẵn sàng tạo video!</p>
        )}
        {testResult === "fail" && (
          <p className="text-red-400 text-sm">✗ {testDetail || "Key không hợp lệ."}</p>
        )}
        {saveMsg && <p className="text-green-400 text-sm">{saveMsg}</p>}
        {saveError && <p className="text-red-400 text-sm">{saveError}</p>}

        <div className="flex gap-3 flex-wrap">
          <button
            type="submit"
            disabled={saving || !keyInput.trim()}
            className="rounded-xl bg-white text-black px-5 py-2 text-sm font-semibold hover:bg-neutral-200 transition disabled:opacity-50"
          >
            {saving ? "Đang lưu..." : t("settings_save_reload")}
          </button>
          <button
            type="button"
            onClick={handleTest}
            disabled={testing || !keyInput.trim()}
            className="rounded-xl border border-neutral-700 px-5 py-2 text-sm font-medium hover:border-neutral-500 transition disabled:opacity-50"
          >
            {testing ? "Đang kiểm tra..." : t("settings_test_api_key")}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-neutral-400">{label}</label>
      {children}
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={[
          "relative inline-flex h-5 w-9 items-center rounded-full transition",
          checked ? "bg-green-500" : "bg-neutral-600",
        ].join(" ")}
      >
        <span
          className={[
            "inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform",
            checked ? "translate-x-4" : "translate-x-1",
          ].join(" ")}
        />
      </button>
      <span className="text-neutral-300">{label}</span>
    </label>
  );
}

function AccountCard({
  account,
  onToggleActive,
  onToggleRotation,
  onDelete,
  deleting,
}: {
  account: GoogleAccount;
  onToggleActive: () => void;
  onToggleRotation: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span
              className={[
                "inline-block h-2 w-2 rounded-full",
                account.is_active ? "bg-green-400" : "bg-neutral-600",
              ].join(" ")}
            />
            <span className="font-medium text-sm">{account.label}</span>
          </div>
          <div className="text-xs text-neutral-500 space-y-0.5 pl-4">
            {account.has_gemini_api_key && <span className="mr-3">🔑 Gemini API Key</span>}
            {account.google_cloud_project && (
              <span className="mr-3">☁ {account.google_cloud_project}</span>
            )}
            {account.use_vertex && <span className="mr-3">⚡ Vertex AI</span>}
            {account.gcs_output_uri && (
              <span className="mr-3 truncate max-w-xs inline-block">{account.gcs_output_uri}</span>
            )}
            {account.last_used_at && (
              <span className="mr-3 text-neutral-600">
                Dùng lần cuối: {new Date(account.last_used_at).toLocaleString("vi-VN")}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-1.5 cursor-pointer text-xs text-neutral-400">
            <MiniToggle checked={account.is_active} onChange={onToggleActive} />
            Kích hoạt
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer text-xs text-neutral-400">
            <MiniToggle checked={account.rotation_enabled} onChange={onToggleRotation} />
            Rotation
          </label>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="text-xs text-red-400 hover:text-red-300 transition disabled:opacity-50 px-2 py-1 rounded-lg hover:bg-red-950/40"
          >
            {deleting ? "Đang xoá..." : "Xoá"}
          </button>
        </div>
      </div>
    </div>
  );
}

function MiniToggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={[
        "relative inline-flex h-4 w-7 items-center rounded-full transition",
        checked ? "bg-green-500" : "bg-neutral-600",
      ].join(" ")}
    >
      <span
        className={[
          "inline-block h-2.5 w-2.5 rounded-full bg-white transition-transform",
          checked ? "translate-x-3.5" : "translate-x-0.5",
        ].join(" ")}
      />
    </button>
  );
}
