export function ProcessingSkeleton() {
  return (
    <section className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-4">
      <div className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm text-slate-500">AI 正在评分中，请稍候…</p>
        <div className="mt-4 space-y-3">
          <div className="h-4 animate-pulse rounded bg-slate-200" />
          <div className="h-4 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
        </div>
      </div>
    </section>
  );
}
