import { NextResponse } from "next/server";

// Async-job SUBMIT proxy. POST a question → the Fly backend creates a job and
// returns its id immediately (well under Vercel's 300s function cap). The agent
// then runs on Fly (no cap); the frontend polls /api/ask/jobs/[id]. This is the
// path that keeps the heaviest golden query (G-1) from 504-ing on the public URL.
export const runtime = "nodejs";
export const maxDuration = 60; // submit returns fast; this is a generous ceiling

const BACKEND_URL = process.env.AGENT_BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  let question = "";
  let session_id: string | undefined;
  let skill: string | undefined;
  try {
    const body = await req.json();
    question = (body?.question ?? "").toString().trim();
    // Forward the upload session (so the agent reads the uploaded files) and the skill toggle.
    session_id = body?.session_id ? String(body.session_id) : undefined;
    skill = body?.skill ? String(body.skill) : undefined;
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }
  if (!question) {
    return NextResponse.json({ error: "question is required" }, { status: 400 });
  }
  try {
    const res = await fetch(`${BACKEND_URL}/api/ask/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        ...(session_id ? { session_id } : {}),
        ...(skill ? { skill } : {}),
      }),
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
