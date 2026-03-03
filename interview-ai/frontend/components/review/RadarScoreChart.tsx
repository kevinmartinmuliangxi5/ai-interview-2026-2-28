"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { EvaluationResult } from "@/types/evaluation";

export interface RadarScoreDatum {
  label: string;
  score: number;
  weight: string;
  fullMark: number;
}

export function buildRadarScoreData(evaluation: EvaluationResult): RadarScoreDatum[] {
  return [
    { label: "综合分析", score: evaluation.analysis_ability_score, weight: "20%", fullMark: 100 },
    { label: "计划组织协调", score: evaluation.organization_coordination_score, weight: "15%", fullMark: 100 },
    { label: "应急应变", score: evaluation.emergency_response_score, weight: "15%", fullMark: 100 },
    { label: "人际沟通", score: evaluation.interpersonal_communication_score, weight: "15%", fullMark: 100 },
    { label: "语言表达", score: evaluation.language_expression_score, weight: "15%", fullMark: 100 },
    { label: "岗位匹配", score: evaluation.job_matching_score, weight: "10%", fullMark: 100 },
    { label: "副语言流畅度", score: evaluation.paralinguistic_fluency_score, weight: "10%", fullMark: 100 },
  ];
}

export function RadarScoreChart({ evaluation }: { evaluation: EvaluationResult }) {
  const data = buildRadarScoreData(evaluation);
  const hasAnyScore = data.some((item) => item.score > 0);

  if (!hasAnyScore) {
    return <p className="text-sm text-slate-500">暂无评分数据。</p>;
  }

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
          <PolarGrid />
          <PolarAngleAxis dataKey="label" />
          <PolarRadiusAxis domain={[0, 100]} tickCount={5} />
          <Radar name="得分" dataKey="score" stroke="#2563EB" fill="#2563EB" fillOpacity={0.25} />
          <Tooltip
            formatter={(value, _name, item) => {
              const payload = item.payload as RadarScoreDatum;
              return [`${value} 分（权重 ${payload.weight}）`, payload.label];
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
