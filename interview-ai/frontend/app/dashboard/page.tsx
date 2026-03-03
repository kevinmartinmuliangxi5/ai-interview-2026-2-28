"use client";

import { useRequireAuth } from "@/lib/auth";

export default function DashboardPage() {
  useRequireAuth();

  return (
    <main className="min-h-screen bg-slate-100 p-8">
      <section className="mx-auto max-w-5xl rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">训练总览</h1>
        <p className="mt-2 text-slate-600">登录成功，后续将接入完整考场流程。</p>
      </section>
    </main>
  );
}
