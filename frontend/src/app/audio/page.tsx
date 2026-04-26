"use client";

import { useEffect, useMemo, useState } from "react";
import DashboardShell from "@/src/components/DashboardShell";
import {
  createAudioMixJob,
  createMusicAsset,
  createNarrationJob,
  createVoiceProfile,
  listMusicAssets,
  listVoiceProfiles,
  type AudioRenderOutput,
  type MusicAsset,
  type NarrationJob,
  type VoiceProfile,
} from "@/src/lib/api";

export default function AudioStudioPage() {
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [musicAssets, setMusicAssets] = useState<MusicAsset[]>([]);
  const [selectedVoiceProfileId, setSelectedVoiceProfileId] = useState<string>("");
  const [selectedMusicAssetId, setSelectedMusicAssetId] = useState<string>("");
  const [scriptText, setScriptText] = useState("Day la doan thu loi dan theo phong cach dien anh. Nhip doc can tu nhien va de theo doi.");
  const [displayName, setDisplayName] = useState("Nguoi dan chuyen A");
  const [consentText, setConsentText] = useState("Toi xac nhan toi so huu giong noi nay hoac da duoc cap phep su dung.");
  const [musicName, setMusicName] = useState("Nen nhac nhe");
  const [musicPrompt, setMusicPrompt] = useState("nen nhac dien anh nhe, khong loi, piano am, nhip nhe");
  const [stylePreset, setStylePreset] = useState("natural_conversational");
  const [breathPreset, setBreathPreset] = useState("cinematic_slow");
  const [narrationJob, setNarrationJob] = useState<NarrationJob | null>(null);
  const [audioOutput, setAudioOutput] = useState<AudioRenderOutput | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const [voices, music] = await Promise.all([listVoiceProfiles(), listMusicAssets()]);
    setVoiceProfiles(voices);
    setMusicAssets(music);
    if (!selectedVoiceProfileId && voices[0]?.id) setSelectedVoiceProfileId(voices[0].id);
    if (!selectedMusicAssetId && music[0]?.id) setSelectedMusicAssetId(music[0].id);
  };

  useEffect(() => {
    void load();
  }, []);

  const selectedVoice = useMemo(
    () => voiceProfiles.find((item) => item.id === selectedVoiceProfileId) || null,
    [voiceProfiles, selectedVoiceProfileId]
  );
  const selectedMusic = useMemo(
    () => musicAssets.find((item) => item.id === selectedMusicAssetId) || null,
    [musicAssets, selectedMusicAssetId]
  );

  const handleCreateVoice = async () => {
    try {
      setBusy(true);
      const created = await createVoiceProfile({
        display_name: displayName,
        clone_mode: "library",
        consent_text: consentText,
        consent_confirmed: true,
      });
      setSelectedVoiceProfileId(created.id);
      await load();
      setMessage(`Da tao ho so giong noi: ${created.display_name}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Khong tao duoc ho so giong noi");
    } finally {
      setBusy(false);
    }
  };

  const handleCreateMusic = async () => {
    try {
      setBusy(true);
      const created = await createMusicAsset({
        display_name: musicName,
        source_mode: "generate",
        provider: "elevenlabs",
        prompt_text: musicPrompt,
        mood: "cinematic",
        force_instrumental: true,
      });
      setSelectedMusicAssetId(created.id);
      await load();
      setMessage(`Da tao tai nguyen nhac: ${created.display_name}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Khong tao duoc tai nguyen nhac");
    } finally {
      setBusy(false);
    }
  };

  const handleGenerateNarration = async () => {
    if (!selectedVoiceProfileId) {
      setMessage("Hay chon hoac tao ho so giong noi truoc.");
      return;
    }
    try {
      setBusy(true);
      const created = await createNarrationJob({
        voice_profile_id: selectedVoiceProfileId,
        script_text: scriptText,
        style_preset: stylePreset,
        breath_pacing_preset: breathPreset,
        provider: "elevenlabs",
      });
      setNarrationJob(created);
      setMessage(`Da tao narration voi ${created.segments.length} doan theo nhip.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Khong tao duoc narration");
    } finally {
      setBusy(false);
    }
  };

  const handleMix = async () => {
    if (!narrationJob?.id) {
      setMessage("Hay tao narration truoc.");
      return;
    }
    try {
      setBusy(true);
      const created = await createAudioMixJob({
        narration_job_id: narrationJob.id,
        music_asset_id: selectedMusicAssetId || undefined,
        mux_to_video: false,
      });
      setAudioOutput(created);
      setMessage(`Trang thai phoi am: ${created.status}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Khong phoi duoc am thanh");
    } finally {
      setBusy(false);
    }
  };

  return (
    <DashboardShell title="Xuong am thanh" description="Ho so giong noi, narration theo nhip tho, nhac nen va pipeline FFmpeg cho long tieng video.">
      <div className="space-y-6">
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border p-4 space-y-3" data-testid="audio-studio-voice-panel">
            <h2 className="text-lg font-semibold">Ho so giong noi</h2>
            <input className="w-full rounded-xl border px-3 py-2" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Ten ho so giong noi" />
            <textarea className="min-h-24 w-full rounded-xl border px-3 py-2" value={consentText} onChange={(e) => setConsentText(e.target.value)} />
            <button className="rounded-xl border px-4 py-2" onClick={handleCreateVoice} disabled={busy}>Tao ho so giong noi an toan</button>
            <select className="w-full rounded-xl border px-3 py-2" value={selectedVoiceProfileId} onChange={(e) => setSelectedVoiceProfileId(e.target.value)}>
              <option value="">Chon ho so giong noi</option>
              {voiceProfiles.map((voice) => (
                <option key={voice.id} value={voice.id}>{voice.display_name} · {voice.clone_mode} · {voice.consent_status}</option>
              ))}
            </select>
            {selectedVoice && <p className="text-sm text-gray-500">Giong noi da chon: {selectedVoice.display_name}</p>}
          </div>

          <div className="rounded-2xl border p-4 space-y-3" data-testid="audio-studio-music-panel">
            <h2 className="text-lg font-semibold">Nhac nen</h2>
            <input className="w-full rounded-xl border px-3 py-2" value={musicName} onChange={(e) => setMusicName(e.target.value)} placeholder="Ten tai nguyen nhac" />
            <textarea className="min-h-24 w-full rounded-xl border px-3 py-2" value={musicPrompt} onChange={(e) => setMusicPrompt(e.target.value)} placeholder="Prompt de sinh nhac nen khong loi" />
            <button className="rounded-xl border px-4 py-2" onClick={handleCreateMusic} disabled={busy}>Sinh nhac nen khong loi</button>
            <select className="w-full rounded-xl border px-3 py-2" value={selectedMusicAssetId} onChange={(e) => setSelectedMusicAssetId(e.target.value)}>
              <option value="">Chon tai nguyen nhac</option>
              {musicAssets.map((music) => (
                <option key={music.id} value={music.id}>{music.display_name} · {music.source_mode}</option>
              ))}
            </select>
            {selectedMusic && <p className="text-sm text-gray-500">Nhac da chon: {selectedMusic.display_name}</p>}
          </div>
        </section>

        <section className="rounded-2xl border p-4 space-y-3" data-testid="audio-studio-narration-panel">
          <h2 className="text-lg font-semibold">Trinh sua narration</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <select className="rounded-xl border px-3 py-2" value={stylePreset} onChange={(e) => setStylePreset(e.target.value)}>
              <option value="natural_conversational">natural_conversational</option>
              <option value="cinematic">cinematic</option>
              <option value="calm">calm</option>
              <option value="energetic">energetic</option>
            </select>
            <select className="rounded-xl border px-3 py-2" value={breathPreset} onChange={(e) => setBreathPreset(e.target.value)}>
              <option value="cinematic_slow">cinematic_slow</option>
              <option value="natural_conversational">natural_conversational</option>
              <option value="explainer_clean">explainer_clean</option>
              <option value="dramatic_documentary">dramatic_documentary</option>
            </select>
          </div>
          <textarea className="min-h-40 w-full rounded-xl border px-3 py-2" value={scriptText} onChange={(e) => setScriptText(e.target.value)} />
          <div className="flex gap-3">
            <button className="rounded-xl border px-4 py-2" onClick={handleGenerateNarration} disabled={busy}>Tao narration</button>
            <button className="rounded-xl border px-4 py-2" onClick={handleMix} disabled={busy || !narrationJob}>Mix giong noi + nhac</button>
          </div>
          {narrationJob && (
            <div className="rounded-xl bg-gray-50 p-3 text-sm" data-testid="audio-studio-narration-result">
              <div>Trang thai: {narrationJob.status}</div>
              <div>Thoi luong: {narrationJob.duration_ms || 0} ms</div>
              <div>So doan: {narrationJob.segments.length}</div>
              <ul className="mt-2 space-y-1">
                {narrationJob.segments.slice(0, 6).map((segment) => (
                  <li key={segment.id}>#{segment.segment_index} · pause {segment.pause_after_ms} ms · {segment.text}</li>
                ))}
              </ul>
            </div>
          )}
          {audioOutput && (
            <div className="rounded-xl bg-gray-50 p-3 text-sm" data-testid="audio-studio-mix-result">
              <div>Trang thai mix: {audioOutput.status}</div>
              <div>URL audio sau mix: {audioOutput.mixed_audio_url || "chua tai len"}</div>
              <div>URL video mux cuoi: {audioOutput.final_muxed_video_url || "chua tao"}</div>
            </div>
          )}
          {message && <p className="text-sm text-gray-600">{message}</p>}
        </section>
      </div>
    </DashboardShell>
  );
}
