"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  getProject,
  getProjectRenderStatus,
  getProjectRenderEvents,
  triggerProjectRender,
  retryProjectRender,
  rerenderScene,
  processTemplateProjectFeedback,
  getCharacterReferencePacks,
  createCharacterReferencePack,
  updateProjectVeoConfig,
  createVeoBatchRun,
  decideRebuild,
  approveRebuild,
} from "@/src/lib/api";
import { useSmartPoll } from "@/src/hooks/useSmartPoll";
import { useT } from "@/src/i18n/useT";
import RebuildDecisionPanel from "@/src/components/RebuildDecisionPanel";
import BudgetPolicySelector, { type BudgetPolicy } from "@/src/components/BudgetPolicySelector";

export default function ProjectWorkspacePage() {
  const params = useParams<{ id: string }>();
  const projectId = Array.isArray(params?.id) ? params.id[0] : (params?.id ?? "");
  const t = useT();
  const [project, setProject] = useState<any>(null);
  const [status, setStatus] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [packs, setPacks] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [veoMode, setVeoMode] = useState("text_to_video");
  const [providerModel, setProviderModel] = useState("veo-3.1-generate-001");
  const [characterReferencePackId, setCharacterReferencePackId] = useState("");
  const [applyLockAll, setApplyLockAll] = useState(true);
  const [previewReferenceMode, setPreviewReferenceMode] = useState(false);
  const [soundGeneration, setSoundGeneration] = useState(false);
  const [startImageUrl, setStartImageUrl] = useState("");
  const [endImageUrl, setEndImageUrl] = useState("");
  const [batchScripts, setBatchScripts] = useState("");
  const [newPackName, setNewPackName] = useState("");
  const [newPackSummary, setNewPackSummary] = useState("");
  const [newPackHeroImage, setNewPackHeroImage] = useState("");
  const [batchResult, setBatchResult] = useState<any>(null);

  // ── Rebuild decision state ─────────────────────────────────────────────
  const [rebuildEpisodeId, setRebuildEpisodeId] = useState("");
  const [rebuildSceneId, setRebuildSceneId] = useState("");
  const [rebuildChangeType, setRebuildChangeType] = useState("subtitle");
  const [budgetPolicy, setBudgetPolicy] = useState<BudgetPolicy>("balanced");
  const [rebuildDecision, setRebuildDecision] = useState<any>(null);
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [rebuildExecuteResult, setRebuildExecuteResult] = useState<any>(null);

  const refresh = async () => {
    const [p, s, e, packData] = await Promise.all([
      getProject(projectId),
      getProjectRenderStatus(projectId),
      getProjectRenderEvents(projectId),
      getCharacterReferencePacks(),
    ]);
    setProject(p);
    setStatus(s);
    setEvents(e.items || []);
    setPacks(packData.items || []);
    if (p?.veo_config) {
      setVeoMode(p.veo_config.veo_mode || "text_to_video");
      setProviderModel(p.veo_config.provider_model || "veo-3.1-generate-001");
      setCharacterReferencePackId(p.veo_config.character_reference_pack_id || "");
      setApplyLockAll(Boolean(p.veo_config.apply_character_lock_to_all_scenes));
      setPreviewReferenceMode(Boolean(p.veo_config.use_preview_reference_mode));
      setSoundGeneration(Boolean(p.veo_config.sound_generation));
    }
    const firstScene = p?.scenes?.[0];
    if (firstScene?.start_image_url) setStartImageUrl(firstScene.start_image_url);
    if (firstScene?.end_image_url) setEndImageUrl(firstScene.end_image_url);
  };

  useEffect(() => {
    void refresh();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const TERMINAL_STATUSES = ["final_ready", "render_failed"] as const;
  type TerminalStatus = (typeof TERMINAL_STATUSES)[number];
  useSmartPoll(refresh, {
    interval: 5000,
    isTerminal: () => TERMINAL_STATUSES.includes(project?.status as TerminalStatus),
    enabled: !!projectId,
  });

  const canRender = project && ["ready_to_render", "draft", "render_failed", "final_ready"].includes(project.status);

  const saveVeoConfig = async () => {
    setBusy(true);
    await updateProjectVeoConfig(projectId, {
      provider_model: providerModel,
      veo_mode: veoMode,
      character_reference_pack_id: characterReferencePackId || null,
      apply_character_lock_to_all_scenes: applyLockAll,
      use_preview_reference_mode: previewReferenceMode,
      sound_generation: soundGeneration,
      scene_inputs: [
        {
          scene_index: 1,
          start_image_url: startImageUrl || null,
          end_image_url: endImageUrl || null,
          character_reference_image_urls: [],
        },
      ],
    });
    await refresh();
    setBusy(false);
  };

  const createPack = async () => {
    setBusy(true);
    await createCharacterReferencePack({
      pack_name: newPackName,
      owner_project_id: projectId,
      identity_summary: newPackSummary,
      appearance_lock_json: { summary: newPackSummary },
      prompt_lock_tokens: [],
      negative_drift_tokens: [],
      images: newPackHeroImage ? [{ image_role: "hero", image_url: newPackHeroImage }] : [],
    });
    setNewPackName("");
    setNewPackSummary("");
    setNewPackHeroImage("");
    await refresh();
    setBusy(false);
  };

  const createBatch = async () => {
    const scripts = batchScripts
      .split("\n---\n")
      .map((x) => x.trim())
      .filter(Boolean)
      .map((script_text, index) => ({ name: `Batch Script ${index + 1}`, script_text, style_preset: project?.style_preset || null }));
    setBusy(true);
    const result = await createVeoBatchRun({
      batch_name: `${project?.name || "Project"} Veo Batch`,
      provider_model: providerModel,
      veo_mode: veoMode,
      aspect_ratio: project?.format || "9:16",
      target_platform: project?.target_platform || "shorts",
      character_reference_pack_id: characterReferencePackId || null,
      apply_character_lock_to_all_scenes: applyLockAll,
      use_preview_reference_mode: previewReferenceMode,
      sound_generation: soundGeneration,
      scene_inputs: [{ scene_index: 1, start_image_url: startImageUrl || null, end_image_url: endImageUrl || null, character_reference_image_urls: [] }],
      scripts,
    });
    setBatchResult(result);
    setBusy(false);
  };

  const handleGetRebuildDecision = async () => {
    if (!rebuildEpisodeId || !rebuildSceneId) return;
    setRebuildLoading(true);
    setRebuildDecision(null);
    setRebuildExecuteResult(null);
    try {
      const decision = await decideRebuild({
        project_id: projectId,
        episode_id: rebuildEpisodeId,
        changed_scene_id: rebuildSceneId,
        change_type: rebuildChangeType,
        budget_policy: budgetPolicy,
      });
      setRebuildDecision(decision);
    } catch (err) {
      setRebuildDecision({ error: err instanceof Error ? err.message : "Decision failed" });
    } finally {
      setRebuildLoading(false);
    }
  };

  const handleApproveRebuild = async (decision: any) => {
    setBusy(true);
    try {
      const result = await approveRebuild(decision);
      setRebuildExecuteResult(result);
      setRebuildDecision(null);
    } catch (err) {
      setRebuildExecuteResult({ error: err instanceof Error ? err.message : "Approve failed" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>{project?.name || t("project_workspace_default_title")}</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
        <section style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
          <h2>{t("project_idea_style")}</h2>
          <div>Idea: {project?.idea}</div>
          <div>Style: {project?.style_preset}</div>
          <div>Platform: {project?.target_platform}</div>
          <div>Format: {project?.format}</div>
          <div>{t("status")}: {project?.status}</div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={async () => { setBusy(true); await triggerProjectRender(projectId); await refresh(); setBusy(false); }} disabled={!canRender || busy}>{t("project_render_video")}</button>
            <button onClick={async () => { setBusy(true); await retryProjectRender(projectId); await refresh(); setBusy(false); }} disabled={busy}>{t("project_retry_render")}</button>
            <button onClick={async () => { setBusy(true); await processTemplateProjectFeedback(projectId); await refresh(); setBusy(false); }} disabled={busy}>{t("project_process_feedback")}</button>
          </div>
        </section>

        <section style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
          <h2>{t("project_render_status_section")}</h2>
          <div>{t("project_current_step")}: {status?.current_step || "-"}</div>
          <div>{t("project_progress")}: {status?.progress_percent || 0}%</div>
          <div>{t("project_render_status_label")}: {status?.render_status || "-"}</div>
          <div>{t("project_fail_reason")}: {status?.fail_reason || "-"}</div>
          {status?.preview_video_url && <div>Preview: <a href={status.preview_video_url}>{t("project_open_preview")}</a></div>}
          {status?.final_video_url && <div>Final: <a href={status.final_video_url}>{t("project_open_final")}</a></div>}
          {status?.thumbnail_url && <div>Thumbnail: <a href={status.thumbnail_url}>{t("project_open_thumbnail")}</a></div>}
        </section>
      </div>

      <section style={{ marginTop: 16, border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>{t("project_veo_controls")}</h2>
        <div style={{ display: "grid", gap: 10 }}>
          <label>{t("project_model_label")}
            <select value={providerModel} onChange={(e) => setProviderModel(e.target.value)}>
              <option value="veo-3.1-generate-001">veo-3.1-generate-001</option>
              <option value="veo-3.1-fast-generate-001">veo-3.1-fast-generate-001</option>
              <option value="veo-3.1-generate-preview">veo-3.1-generate-preview</option>
              <option value="veo-3.1-fast-generate-preview">veo-3.1-fast-generate-preview</option>
            </select>
          </label>
          <label>{t("project_mode_label")}
            <select value={veoMode} onChange={(e) => setVeoMode(e.target.value)}>
              <option value="text_to_video">{t("project_mode_text_to_video")}</option>
              <option value="image_to_video">{t("project_mode_image_to_video")}</option>
              <option value="first_last_frames">{t("project_mode_first_last")}</option>
              <option value="reference_image_to_video">{t("project_mode_reference")}</option>
            </select>
          </label>
          <label>{t("project_character_pack_label")}
            <select value={characterReferencePackId} onChange={(e) => setCharacterReferencePackId(e.target.value)}>
              <option value="">None</option>
              {packs.map((p: any) => <option key={p.id} value={p.id}>{p.pack_name}</option>)}
            </select>
          </label>
          <label>{t("project_start_image_url")}
            <input value={startImageUrl} onChange={(e) => setStartImageUrl(e.target.value)} />
          </label>
          <label>{t("project_end_image_url")}
            <input value={endImageUrl} onChange={(e) => setEndImageUrl(e.target.value)} />
          </label>
          <label><input type="checkbox" checked={applyLockAll} onChange={(e) => setApplyLockAll(e.target.checked)} /> {t("project_apply_character_lock")}</label>
          <label><input type="checkbox" checked={previewReferenceMode} onChange={(e) => setPreviewReferenceMode(e.target.checked)} /> {t("project_preview_reference_mode")}</label>
          <label><input type="checkbox" checked={soundGeneration} onChange={(e) => setSoundGeneration(e.target.checked)} /> {t("project_sound_generation")}</label>
          <button onClick={saveVeoConfig} disabled={busy}>{t("project_save_veo_config")}</button>
        </div>
      </section>

      <section style={{ marginTop: 16, border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>{t("project_character_pack_section")}</h2>
        <div style={{ display: "grid", gap: 8 }}>
          <input placeholder={t("project_pack_name_placeholder")} value={newPackName} onChange={(e) => setNewPackName(e.target.value)} />
          <textarea placeholder={t("project_identity_summary_placeholder")} value={newPackSummary} onChange={(e) => setNewPackSummary(e.target.value)} />
          <input placeholder={t("project_hero_image_placeholder")} value={newPackHeroImage} onChange={(e) => setNewPackHeroImage(e.target.value)} />
          <button onClick={createPack} disabled={busy || !newPackName}>{t("project_create_pack")}</button>
        </div>
      </section>

      <section style={{ marginTop: 16, border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>{t("project_veo_batch_run")}</h2>
        <p>{t("project_batch_separator_hint")}</p>
        <textarea rows={10} value={batchScripts} onChange={(e) => setBatchScripts(e.target.value)} style={{ width: "100%" }} />
        <div style={{ marginTop: 8 }}>
          <button onClick={createBatch} disabled={busy || !batchScripts.trim()}>{t("project_create_batch")}</button>
        </div>
        {batchResult && (
          <div style={{ marginTop: 12 }}>
            <div>{t("project_batch_id")}: {batchResult.veo_batch_run_id}</div>
            <div>{t("project_total_scripts")}: {batchResult.total_scripts}</div>
            <div>{t("status")}: {batchResult.status}</div>
          </div>
        )}
      </section>

      <section style={{ marginTop: 16, border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>{t("scenes")}</h2>
        <div style={{ display: "grid", gap: 10 }}>
          {(project?.scenes || []).map((scene: any) => (
            <div key={scene.scene_index} style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
              <div><strong>{t("scene")} {scene.scene_index} — {scene.title}</strong></div>
              <div>{scene.script_text}</div>
              <div>{t("time")}: {scene.target_duration_sec}s</div>
              <div>{t("project_mode_label")}: {scene.provider_mode || veoMode}</div>
              <button onClick={async () => { setBusy(true); await rerenderScene(projectId, scene.scene_index); await refresh(); setBusy(false); }} disabled={busy}>
                {t("project_rerender_scene")}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 16, border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>{t("project_render_events")}</h2>
        <div style={{ display: "grid", gap: 8 }}>
          {events.map((event: any) => (
            <div key={event.id} style={{ borderBottom: "1px solid #eee", paddingBottom: 8 }}>
              <div><strong>{event.event_type}</strong> — {event.status || "-"}</div>
              <div>{t("scene")}: {event.scene_index ?? "-"}</div>
              <div>{t("project_at_label")}: {event.occurred_at || "-"}</div>
              <div>{event.error_message || ""}</div>
            </div>
          ))}
        </div>
      </section>
      <section style={{ marginTop: 16, border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
        <h2>{t("rebuild_decision_title")}</h2>
        <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
          <input
            placeholder="Episode ID"
            value={rebuildEpisodeId}
            onChange={(e) => setRebuildEpisodeId(e.target.value)}
          />
          <input
            placeholder="Changed Scene ID"
            value={rebuildSceneId}
            onChange={(e) => setRebuildSceneId(e.target.value)}
          />
          <select value={rebuildChangeType} onChange={(e) => setRebuildChangeType(e.target.value)}>
            <option value="subtitle">subtitle</option>
            <option value="voice">voice</option>
            <option value="avatar">avatar</option>
            <option value="timeline">timeline</option>
          </select>
          <BudgetPolicySelector value={budgetPolicy} onChange={setBudgetPolicy} />
          <button
            onClick={handleGetRebuildDecision}
            disabled={rebuildLoading || !rebuildEpisodeId || !rebuildSceneId}
          >
            {t("project_get_rebuild_decision")}
          </button>
        </div>
        <RebuildDecisionPanel
          decision={rebuildDecision}
          loading={rebuildLoading}
          onApprove={handleApproveRebuild}
          onCancel={() => setRebuildDecision(null)}
        />
        {rebuildExecuteResult && (
          <div style={{ marginTop: 12, padding: 8, background: "#f0f0f0", borderRadius: 4 }}>
            <strong>Execute result:</strong> {JSON.stringify(rebuildExecuteResult)}
          </div>
        )}
      </section>

    </main>
  );
}
