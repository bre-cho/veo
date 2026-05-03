"use client";
import { toPng } from "html-to-image";

export function ExportButton() {
  async function exportImage() {
    const el = document.getElementById("poster-canvas-root");
    if (!el) return alert("Không tìm thấy canvas");

    const dataUrl = await toPng(el, { pixelRatio: 2 });
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = "poster.png";
    a.click();
  }

  return <button className="btn" onClick={exportImage}>Ẩnh PNG</button>;
}
