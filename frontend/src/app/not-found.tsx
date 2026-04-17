export default function NotFound() {
  return (
    <main className="min-h-screen bg-neutral-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <h1 className="text-3xl font-semibold tracking-tight">404 - Page Not Found</h1>
          <p className="mt-2 text-sm text-white/60">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </header>
        <div>
          <a
            href="/"
            className="inline-block rounded-2xl bg-sky-500/20 px-6 py-3 text-sm font-semibold text-sky-400 transition hover:bg-sky-500/30"
          >
            Return to Home
          </a>
        </div>
      </div>
    </main>
  );
}
