interface AnswerComparisonProps {
  userAnswer: string;
  modelAnswer: string;
}

export function AnswerComparison({ userAnswer, modelAnswer }: AnswerComparisonProps) {
  return (
    <section className="rounded-xl border border-slate-200 p-4">
      <h2 className="text-lg font-semibold text-slate-900">答案对照</h2>
      <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <h3 className="text-sm font-semibold text-slate-700">考生原文</h3>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{userAnswer}</p>
        </div>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <h3 className="text-sm font-semibold text-blue-700">AI 示范答案</h3>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-blue-800">{modelAnswer}</p>
        </div>
      </div>
    </section>
  );
}
