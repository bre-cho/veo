"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Loi ung dung:", error);
  }, [error]);

  return (
    <main className="min-h-screen bg-neutral-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-red-500/20 bg-red-500/10 p-6">
          <h1 className="text-3xl font-semibold tracking-tight text-red-400">
            Loi ung dung
          </h1>
          <p className="mt-2 text-sm text-red-300/70">
            {error.message || "Da xay ra loi khong mong doi khi tai trang nay."}
          </p>
          {error.digest && (
            <p className="mt-1 text-xs font-mono text-red-300/50">Ma loi: {error.digest}</p>
          )}
        </header>
        <div className="flex gap-4">
          <button
            onClick={() => reset()}
            className="inline-block rounded-2xl bg-amber-500/20 px-6 py-3 text-sm font-semibold text-amber-400 transition hover:bg-amber-500/30"
          >
            Thu lai
          </button>
          <a
            href="/"
            className="inline-block rounded-2xl bg-sky-500/20 px-6 py-3 text-sm font-semibold text-sky-400 transition hover:bg-sky-500/30"
          >
            Ve trang chu
          </a>
        </div>
      </div>
    </main>
  );
}
