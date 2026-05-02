"use client";

import { useState } from "react";

export function AgentStreamingConsole() {
  const [input, setInput] = useState({
    industry: "SaaS",
    product: "AI Design Tool",
    audience: "seller, marketer, creator",
    goal: "Lead",
    platform: "TikTok"
  });
  const [blocks, setBlocks] = useState<any[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setError("");
    setBlocks([]);
    setRunning(true);
    const res = await fetch("/api/orchestrator/stream", { method: "POST", body: JSON.stringify(input) });
    if (!res.ok) {
      setError("Không thể khởi chạy orchestrator.");
      setRunning(false);
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      setError("Không nhận được stream dữ liệu.");
      setRunning(false);
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        const eventLine = chunk.split("\n").find((l) => l.startsWith("event:"));
        const dataLine = chunk.split("\n").find((l) => l.startsWith("data:"));
        if (!eventLine || !dataLine) continue;

        const event = eventLine.replace("event:", "").trim();
        let data: any = {};
        try {
          data = JSON.parse(dataLine.replace("data:", "").trim());
        } catch {
          continue;
        }

        if (event === "agent_start") setBlocks((p) => [...p, { agent: data.agent, status: "running" }]);
        if (event === "agent_done") setBlocks((p) => p.map((b) => b.agent === data.agent ? { ...b, status: "done", output: data.output } : b));
        if (event === "done") setRunning(false);
      }
    }
    setRunning(false);
  }

  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>AI Ads Factory Orchestrator</h1>
      <section className="card" style={{ marginTop: 24 }}>
        <input value={input.product} onChange={(e) => setInput({ ...input, product: e.target.value })} />
        <button className="btn" style={{ marginLeft: 12 }} onClick={run}>{running ? "Đang chạy..." : "Run Full Factory"}</button>
      </section>

      {error && <p style={{ color: "#FCA5A5", marginTop: 20 }}>{error}</p>}

      <section style={{ marginTop: 24, display: "grid", gap: 16 }}>
        {blocks.map((b) => (
          <div className="card" key={b.agent}>
            <h2>{b.status === "running" ? "🟡" : "🟢"} {b.agent}</h2>
            <pre style={{ whiteSpace: "pre-wrap", color: "#CBD5E1" }}>{b.output || "Đang tạo output..."}</pre>
          </div>
        ))}
      </section>
    </main>
  );
}
