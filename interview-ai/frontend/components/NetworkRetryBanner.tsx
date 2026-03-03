"use client";

interface NetworkRetryBannerProps {
  visible: boolean;
  message?: string;
  onRetry: () => void;
}

export function NetworkRetryBanner({ visible, message, onRetry }: NetworkRetryBannerProps) {
  if (!visible) {
    return null;
  }

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-800">
      <p className="text-sm">{message || "网络异常，请保持页面勿刷新。"}</p>
      <button
        type="button"
        onClick={onRetry}
        className="min-h-12 min-w-12 mt-3 rounded-lg bg-amber-600 px-4 py-2 text-white"
      >
        重试上传
      </button>
    </div>
  );
}
