import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const backendUrl = process.env.API_BASE_URL;
  if (!backendUrl) {
    return NextResponse.json(
      { error_code: "ERR_INTERNAL", message: "Backend URL not configured." },
      { status: 500 },
    );
  }

  const authHeader = request.headers.get("authorization");
  if (!authHeader) {
    return NextResponse.json({ error_code: "ERR_UNAUTHORIZED" }, { status: 401 });
  }

  const formData = await request.formData();
  const clientRequestId = (formData.get("client_request_id") as string) || crypto.randomUUID();
  formData.set("client_request_id", clientRequestId);

  try {
    const response = await fetch(`${backendUrl}/api/v1/evaluations/submit`, {
      method: "POST",
      headers: {
        Authorization: authHeader,
      },
      body: formData,
      cache: "no-store",
    });

    const text = await response.text();
    try {
      const json = JSON.parse(text);
      return NextResponse.json(json, { status: response.status });
    } catch {
      return NextResponse.json(
        { error_code: "ERR_BAD_GATEWAY", message: text || "Invalid response from backend." },
        { status: response.status },
      );
    }
  } catch {
    return NextResponse.json(
      { error_code: "ERR_NETWORK", message: "网络异常，请稍后重试。" },
      { status: 503 },
    );
  }
}
