import { NextResponse } from "next/server";

// Upload proxy. The browser POSTs multipart/form-data (the user's CSV/PDF/xlsx) here;
// we forward it unchanged to the Fly backend's /api/uploads, which validates type/size,
// stores the files in a fresh per-session dir, pre-extracts PDFs, and returns
// { session_id, files }. The frontend then carries that session_id on the subsequent ask
// so the agent answers over the uploaded files. We stream the incoming form body straight
// through — no buffering of the whole upload into a JSON body.
export const runtime = "nodejs";
export const maxDuration = 60; // upload + PDF pre-extract; well under the cap

const BACKEND_URL = process.env.AGENT_BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ error: "invalid multipart form" }, { status: 400 });
  }
  const files = form.getAll("files").filter((f): f is File => f instanceof File);
  if (files.length === 0) {
    return NextResponse.json({ error: "no files uploaded" }, { status: 400 });
  }
  // Re-pack into a fresh FormData so fetch sets a correct multipart boundary for the backend.
  const out = new FormData();
  for (const f of files) out.append("files", f, f.name);
  try {
    const res = await fetch(`${BACKEND_URL}/api/uploads`, { method: "POST", body: out });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "backend unreachable" },
      { status: 502 }
    );
  }
}
