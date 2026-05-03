import fs from "fs";
import path from "path";

export async function renderAdVideo(inputProps: any) {
  const { bundle } = await import("@remotion/bundler");
  const { renderMedia, selectComposition } = await import("@remotion/renderer");

  const renderDir = path.join(process.cwd(), "public", "renders");
  fs.mkdirSync(renderDir, { recursive: true });

  const entry = path.join(process.cwd(), "remotion", "index.js");
  const serveUrl = await bundle(entry);

  const composition = await selectComposition({
    serveUrl,
    id: "AdVideo",
    inputProps
  });

  const filename = `${Date.now()}-ad.mp4`;
  const outputLocation = path.join(renderDir, filename);

  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    outputLocation,
    inputProps
  });

  return `/renders/${filename}`;
}
