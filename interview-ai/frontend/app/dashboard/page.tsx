"use client";

import { useRouter } from "next/navigation";

import { DeviceCheck } from "@/components/DeviceCheck";
import { useRequireAuth } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  useRequireAuth();

  return (
    <main className="min-h-screen bg-slate-100 p-8">
      <section className="mx-auto grid max-w-5xl gap-6">
        <article className="rounded-2xl bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">训练总览</h1>
          <p className="mt-2 text-slate-600">完成设备检测后，开始模拟面试流程。</p>
        </article>
        <DeviceCheck onReady={() => router.push("/interview/mock")} />
      </section>
    </main>
  );
}
