interface ImprovementListProps {
  suggestions: string[];
}

export function ImprovementList({ suggestions }: ImprovementListProps) {
  return (
    <section className="rounded-xl border border-slate-200 p-4">
      <h2 className="text-lg font-semibold text-slate-900">改进建议</h2>
      {suggestions.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">暂无改进建议。</p>
      ) : (
        <ol className="mt-2 list-inside list-decimal space-y-2 text-sm leading-6 text-slate-700">
          {suggestions.map((item, index) => (
            <li key={`${index}-${item}`}>{item}</li>
          ))}
        </ol>
      )}
    </section>
  );
}
