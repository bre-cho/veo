export function SaasShell({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-screen bg-[#050816] text-white">
      <section className="relative overflow-hidden border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(37,99,235,.32),transparent_32%),radial-gradient(circle_at_85%_10%,rgba(245,158,11,.20),transparent_28%)]" />
        <div className="relative mx-auto max-w-7xl px-5 py-14">
          <p className="text-sm font-black uppercase tracking-[0.28em] text-amber-300">{eyebrow}</p>
          <h1 className="mt-4 max-w-5xl text-5xl font-black leading-tight tracking-tight text-white md:text-6xl">
            {title}
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">{subtitle}</p>
        </div>
      </section>
      {children}
    </main>
  );
}
