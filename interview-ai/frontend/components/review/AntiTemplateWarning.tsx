interface AntiTemplateWarningProps {
  warning: string | null;
}

export function AntiTemplateWarning({ warning }: AntiTemplateWarningProps) {
  if (warning === null) {
    return null;
  }

  return (
    <section className="rounded-xl border border-yellow-400 bg-yellow-50 p-4">
      <h2 className="text-lg font-semibold text-yellow-800">反模板化提醒</h2>
      <p className="mt-1 text-sm text-yellow-700">{warning}</p>
    </section>
  );
}
