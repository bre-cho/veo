import { NextRequest, NextResponse } from "next/server";

function resolveApiBaseUrl(): string {
  const raw =
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!raw && process.env.NODE_ENV === "production") {
    throw new Error(
      "API_BASE_URL (or NEXT_PUBLIC_API_BASE_URL) is not set. " +
      "This environment variable is required in production."
    );
  }

  return (raw || "http://localhost:8000/api/v1").replace(/\/+$/, "");
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await context.params;
  const base = resolveApiBaseUrl();
  const target = `${base}/render/jobs/${jobId}`;

  try {
    const response = await fetch(target, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
        "X-Frontend-Snapshot-Proxy": "render-job",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: {
          message:
            error instanceof Error ? error.message : "Frontend snapshot proxy failed",
        },
      },
      { status: 502 },
    );
  }
}
