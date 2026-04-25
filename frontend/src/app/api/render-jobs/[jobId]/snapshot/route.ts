import { NextRequest, NextResponse } from "next/server";
import { getRequiredApiBaseUrl } from "@/src/lib/get-api-url";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await context.params;
  const base = getRequiredApiBaseUrl();
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
