"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { createSessionStorageSupabaseClient } from "@/lib/supabase";

export function useRequireAuth() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const token = window.sessionStorage.getItem("access_token");
    if (!token) {
      document.cookie = "auth-present=; path=/; Max-Age=0";
      document.cookie = "access-token=; path=/; Max-Age=0";
      router.replace("/login");
      return;
    }

    const supabase = createSessionStorageSupabaseClient();
    supabase.auth.getUser().then(({ data, error }) => {
      if (error || !data.user) {
        window.sessionStorage.clear();
        document.cookie = "auth-present=; path=/; Max-Age=0";
        document.cookie = "access-token=; path=/; Max-Age=0";
        router.replace("/login");
      }
    });
  }, [router]);
}
