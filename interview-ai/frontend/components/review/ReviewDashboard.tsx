import type { EvaluationResult } from "@/types/evaluation";

interface ReviewDashboardProps {
  evaluation: EvaluationResult;
}

export function ReviewDashboard({ evaluation }: ReviewDashboardProps) {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <section className="mx-auto max-w-5xl rounded-2xl bg-white p-6 shadow-sm md:p-8">
        <h1 className="text-2xl font-semibold text-slate-900">评估结果</h1>
        <p className="mt-2 text-sm text-slate-600">记录 ID：{evaluation.id}</p>
        <p className="mt-2 text-sm text-slate-600">综合得分：{evaluation.final_score}</p>
      </section>
    </main>
  );
}
