import { AntiTemplateWarning } from "@/components/review/AntiTemplateWarning";
import { AnswerComparison } from "@/components/review/AnswerComparison";
import { AudioTranscriptSync } from "@/components/review/AudioTranscriptSync";
import { ImprovementList } from "@/components/review/ImprovementList";
import { RadarScoreChart } from "@/components/review/RadarScoreChart";
import { StructuralCheck } from "@/components/review/StructuralCheck";
import type { EvaluationResult } from "@/types/evaluation";

interface ReviewDashboardProps {
  evaluation: EvaluationResult;
}

export function ReviewDashboard({ evaluation }: ReviewDashboardProps) {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <section className="mx-auto max-w-5xl space-y-6 rounded-2xl bg-white p-6 shadow-sm md:p-8">
        <header>
          <h1 className="text-2xl font-semibold text-slate-900">评估结果</h1>
          <p className="mt-2 text-sm text-slate-600">记录 ID：{evaluation.id}</p>
          <p className="mt-1 text-sm text-slate-600">综合得分：{evaluation.final_score}</p>
        </header>

        <AntiTemplateWarning warning={evaluation.anti_template_warning} />

        <section className="rounded-xl border border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900">七维雷达图</h2>
          <p className="mt-1 text-sm text-slate-500">悬停可查看每个维度得分和权重。</p>
          <div className="mt-4">
            <RadarScoreChart evaluation={evaluation} />
          </div>
        </section>

        <AudioTranscriptSync audioSrc={evaluation.audio_storage_path} segments={evaluation.transcript_segments} />

        <AnswerComparison userAnswer={evaluation.transcript} modelAnswer={evaluation.model_ideal_answer} />

        <StructuralCheck check={evaluation.structural_framework_check} />

        <ImprovementList suggestions={evaluation.improvement_suggestions} />
      </section>
    </main>
  );
}
