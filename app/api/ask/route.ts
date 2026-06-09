import { NextResponse } from "next/server";

// The agentic engine is a Python FastAPI backend running the Claude Agent SDK.
// This route is a thin proxy: it forwards the question and returns the Aletheia
// output contract { answer, evidence, trace, validation } unchanged.
export const runtime = "nodejs";
export const maxDuration = 300; // agent loops can take a while

const BACKEND_URL = process.env.AGENT_BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  let question = "";
  try {
    const body = await req.json();
    question = (body?.question ?? "").toString().trim();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }
  if (!question) {
    return NextResponse.json({ error: "question is required" }, { status: 400 });
  }
  try {
    const res = await fetch(`${BACKEND_URL}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "backend unreachable" },
      { status: 502 }
    );
  }
}
