import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ReviewDashboard } from "@/components/review/ReviewDashboard";
import { loadEvaluationById } from "@/lib/reviewDataLoader";

interface ReviewPageProps {
  params: {
    id: string;
  };
}

export default async function ReviewPage({ params }: ReviewPageProps) {
  const accessToken = cookies().get("access-token")?.value;
  if (!accessToken) {
    redirect("/login");
  }

  const result = await loadEvaluationById({
    backendUrl: process.env.API_BASE_URL ?? "",
    evaluationId: params.id,
    accessToken,
  });

  if (result.state === "unauthorized") {
    redirect("/login");
  }

  if (result.state === "not_found") {
    return (
      <main className="min-h-screen bg-slate-100 px-4 py-8">
        <section className="mx-auto max-w-3xl rounded-2xl bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">记录不存在</h1>
          <p className="mt-2 text-sm text-slate-600">请返回面板重新发起一次模拟面试。</p>
        </section>
      </main>
    );
  }

  if (result.state === "error") {
    return (
      <main className="min-h-screen bg-slate-100 px-4 py-8">
        <section className="mx-auto max-w-3xl rounded-2xl bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">加载失败</h1>
          <p className="mt-2 text-sm text-red-600">{result.message}</p>
        </section>
      </main>
    );
  }

  return <ReviewDashboard evaluation={result.evaluation} />;
}
