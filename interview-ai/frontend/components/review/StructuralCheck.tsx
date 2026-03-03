import type { StructuralFrameworkCheck } from "@/types/evaluation";

interface StructuralCheckProps {
  check: StructuralFrameworkCheck;
}

export function StructuralCheck({ check }: StructuralCheckProps) {
  return (
    <section className="rounded-xl border border-slate-200 p-4">
      <h2 className="text-lg font-semibold text-slate-900">结构检查</h2>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <h3 className="text-sm font-semibold text-emerald-700">已覆盖要素</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {check.present_elements.length === 0 ? (
              <span className="text-sm text-emerald-700/80">暂无</span>
            ) : (
              check.present_elements.map((item) => (
                <span key={item} className="rounded-full bg-emerald-100 px-2 py-1 text-xs text-emerald-800">
                  {item}
                </span>
              ))
            )}
          </div>
        </div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <h3 className="text-sm font-semibold text-rose-700">缺失要素</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {check.missing_elements.length === 0 ? (
              <span className="text-sm text-rose-700/80">无</span>
            ) : (
              check.missing_elements.map((item) => (
                <span key={item} className="rounded-full bg-rose-100 px-2 py-1 text-xs text-rose-800">
                  {item}
                </span>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
