"use client";
import { useEditorStore } from "@/lib/editor/editor-store";

export function ImageUploadButton() {
  const { updateElement, doc } = useEditorStore();

  function upload(file: File) {
    const url = URL.createObjectURL(file);
    const img = doc.elements.find(e => e.type === "image");
    if (!img) return alert("No image layer");

    updateElement(img.id, { src: url });
  }

  return (
    <label className="btn">
      Upload
      <input type="file" hidden onChange={(e) => {
        const f = e.target.files?.[0];
        if (f) upload(f);
      }} />
    </label>
  );
}
