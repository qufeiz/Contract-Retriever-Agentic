import { NextResponse } from "next/server";

// Async-job POLL proxy. GET a job id → the Fly backend returns {status, trace,
// result?, error?}. Each poll is a short request (just reads in-memory job state
// on Fly), so it never approaches the Vercel function cap no matter how long the
// underlying agent run takes. The frontend polls this until status is done/error.
export const runtime = "nodejs";
export const maxDuration = 30;

const BACKEND_URL = process.env.AGENT_BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!id) {
    return NextResponse.json({ error: "job id is required" }, { status: 400 });
  }
  try {
    const res = await fetch(`${BACKEND_URL}/api/ask/jobs/${encodeURIComponent(id)}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "backend unreachable", status: "error" },
      { status: 502 }
    );
  }
}
