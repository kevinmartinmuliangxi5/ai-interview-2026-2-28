interface ReviewPageProps {
  params: {
    id: string;
  };
}

export default function ReviewPage({ params }: ReviewPageProps) {
  return (
    <main className="min-h-screen bg-slate-100 p-8">
      <section className="mx-auto max-w-4xl rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">评估结果</h1>
        <p className="mt-2 text-slate-600">评估记录 ID：{params.id}</p>
        <p className="mt-4 text-sm text-slate-500">复盘看板将在 Milestone 3 完整接入。</p>
      </section>
    </main>
  );
}
