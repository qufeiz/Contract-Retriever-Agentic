"use client";
import { useState, useRef, useEffect } from "react";

// The agentic engine returns the Aletheia output contract. `evidence` is a flat
// list of resolvable sources (file + locator); `trace` is the agent's work log
// (maps read, files opened) shown in the TRACE panel.
type EvidenceItem = { file: string; loc: string; snippet: string };
type TraceStep = { kind: string; detail: string };
type AnswerResult = {
  question: string;
  answer: string;
  evidence: EvidenceItem[];
  trace: TraceStep[];
  validation: { ok: boolean; reasons: string[] };
};

// One uploaded file, as the backend describes it after /api/uploads. `columns`/`rows`
// are set for CSV/xlsx; `pages` for PDF — shown so the user sees what the agent will read.
type UploadedFile = {
  name: string;
  kind: "csv" | "pdf" | "xlsx";
  size: number;
  columns: string[];
  pages: number | null;
  rows: number | null;
};

// Per-feature entry points — color-coded so the surface reads as "many capabilities".
const EXAMPLES: { feat: string; chip: string; q: string }[] = [
  {
    feat: "Contract Intelligence",
    chip: "var(--sql)",
    q: "What contracts expire in the next 90 days and what penalties are defined in those contracts?",
  },
  {
    feat: "Case File Q&A",
    chip: "var(--pdf)",
    q: "What was the final child support amount, and who got primary residence in the Carter case?",
  },
  {
    feat: "Case File Q&A",
    chip: "var(--pdf)",
    q: "When did Joni Carter file for divorce?",
  },
  {
    feat: "Maintenance Spend",
    chip: "var(--gold)",
    q: "Which customers have overdue payments and what does the agreement say about service suspension?",
  },
  {
    feat: "Maintenance Spend",
    chip: "var(--gold)",
    q: "How much did we spend on maintenance in 2026, and which vendors cost the most overall?",
  },
  {
    feat: "Contract Intelligence · עברית",
    chip: "var(--sql)",
    q: "אילו חוזים יפוגו ב-90 הימים הקרובים ומהם הקנסות המוגדרים באותם חוזים?",
  },
];

// Citation token grammar: [F:<file>#<locator>]. The file path decides the chip
// color — carter-case PDFs read "document" (pdf), school-operations CSVs read
// "structured" (sql).
const CITE_RE = /(\[F:[^\]#]+#[^\]]+\])/g;
const isHebrew = (s: string) => /[֐-׿]/.test(s);

function parseToken(token: string): { file: string; loc: string } | null {
  const m = token.match(/^\[F:([^\]#]+)#([^\]]+)\]$/);
  return m ? { file: m[1], loc: m[2] } : null;
}
const isPdfFile = (file: string) => /\.pdf$/i.test(file) || file.startsWith("carter-case/");
const fileLabel = (file: string) => file.split("/").pop() ?? file;
const locLabel = (loc: string) => {
  const p = loc.match(/^p(\d+)$/i);
  if (p) return `page ${p[1]}`;
  const ord = loc.match(/^row-(\d+)$/i); // uploaded CSV/xlsx ordinal row
  if (ord) return `row ${ord[1]}`;
  const r = loc.match(/^row=(.+)$/);
  if (r) return `row ${r[1]}`;
  return loc;
};

// Async-job polling cadence. Submit returns a job id fast; we then poll the
// status endpoint, surfacing the live agent trace until status is done/error.
// Each poll is a short request, so a multi-minute agent run never 504s — the
// long work lives on Fly (no request cap), not in a single Vercel function call.
const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 12 * 60 * 1000; // generous ceiling for the heaviest agent run

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Home() {
  const [question, setQuestion] = useState("");
  // Retrieval-skill toggle: "full" (kb-retriever) vs "lean" (kb-retriever-lean — slimmer prompt,
  // cheaper/faster, same grounding+citations). Sent on every ask; honored on the committed-corpus
  // path (the upload path uses its own self-contained prompt).
  const [skill, setSkill] = useState<"full" | "lean">("full");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeCite, setActiveCite] = useState<string | null>(null);
  // The live agent trace while a job is running (streamed via polling).
  const [liveTrace, setLiveTrace] = useState<TraceStep[]>([]);
  // Live-upload session: the files the user uploaded + the session_id carried on the ask.
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sourcesRef = useRef<HTMLDivElement>(null);

  // Send the chosen files to the backend → get back a session_id + the parsed file list.
  // The subsequent ask carries that session_id so the agent reads the uploaded files.
  async function uploadFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length === 0) return;
    setUploading(true);
    setUploadError(null);
    try {
      const fd = new FormData();
      for (const f of list) fd.append("files", f, f.name);
      const res = await fetch("/api/uploads", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "upload failed");
      setSessionId(data.session_id as string);
      setUploads(data.files as UploadedFile[]);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "upload failed");
      setSessionId(null);
      setUploads([]);
    } finally {
      setUploading(false);
    }
  }

  function clearUploads() {
    setSessionId(null);
    setUploads([]);
    setUploadError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function ask(q: string) {
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveCite(null);
    setLiveTrace([]);
    try {
      // 1. Submit the question → get a job id back immediately (under the cap). When the
      // user has uploaded files, the session_id rides along so the agent reads them.
      const submit = await fetch("/api/ask/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, skill, ...(sessionId ? { session_id: sessionId } : {}) }),
      });
      const job = await submit.json();
      if (!submit.ok) throw new Error(job.error ?? "request failed");
      const jobId: string = job.job_id;
      if (!jobId) throw new Error("backend did not return a job id");

      // 2. Poll the job → stream the live agent trace, then the final answer.
      const started = Date.now();
      // eslint-disable-next-line no-constant-condition
      while (true) {
        if (Date.now() - started > POLL_TIMEOUT_MS) {
          throw new Error("the agent run took too long — please try again");
        }
        await sleep(POLL_INTERVAL_MS);
        const poll = await fetch(`/api/ask/jobs/${encodeURIComponent(jobId)}`);
        const data = await poll.json();
        if (!poll.ok) throw new Error(data.error ?? "polling failed");
        if (Array.isArray(data.trace)) setLiveTrace(data.trace as TraceStep[]);
        if (data.status === "done" && data.result) {
          setResult(data.result as AnswerResult);
          return;
        }
        if (data.status === "error") {
          throw new Error(data.error ?? "the agent run failed");
        }
        // status === "running" → keep polling.
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "request failed");
    } finally {
      setLoading(false);
    }
  }

  // Click a citation chip → highlight + scroll to the matching evidence source.
  function onCiteClick(token: string) {
    setActiveCite(token);
  }
  useEffect(() => {
    if (!activeCite) return;
    const el = document.getElementById(`src-${cssId(activeCite)}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeCite]);

  function renderAnswer(text: string) {
    return text.split(CITE_RE).map((p, i) => {
      const parsed = parseToken(p);
      if (parsed) {
        const cls = isPdfFile(parsed.file) ? "cite pdf" : "cite sql";
        return (
          <span
            key={i}
            className={`${cls}${activeCite === p ? " active" : ""}`}
            title="Click to trace this claim to its source"
            role="button"
            tabIndex={0}
            onClick={() => onCiteClick(p)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onCiteClick(p)}
          >
            [{fileLabel(parsed.file)}#{parsed.loc}]
          </span>
        );
      }
      return <span key={i}>{p}</span>;
    });
  }

  const evidence = result?.evidence ?? [];
  const trace = result?.trace ?? [];
  const answerRtl = result ? isHebrew(result.answer) : false;

  return (
    <div className="wrap">
      <header className="masthead">
        <div className="brand-row">
          <h1 className="wordmark">
            Aletheia<span className="dot">.</span>
          </h1>
          <span className="kicker">Agentic Knowledge Assistant</span>
        </div>
        <p className="tagline">
          Ask a business question in plain language. Aletheia is an <b>agent</b> that navigates the
          knowledge base, <b>reads the real files</b>, and attaches a <b>citation to every fact</b>{" "}
          you can trace to the exact page or row. Not a PDF chatbot — grounded, or it says so.
        </p>
      </header>

      <form
        className="ask"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim() && !loading) ask(question.trim());
        }}
      >
        <span className="glyph" aria-hidden>
          ❧
        </span>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about contracts, the case file, or maintenance spend…"
          aria-label="Ask a question"
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? <span className="spinner" /> : "Ask"}
        </button>
      </form>

      {/* Retrieval-skill toggle: lean ⇄ full. Lean uses a slimmer skill prompt (cheaper/faster);
          full is the thorough navigator. Same grounding + citations either way. */}
      <div
        className="skill-toggle"
        role="radiogroup"
        aria-label="Retrieval skill"
        data-testid="skill-toggle"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          margin: "10px 2px 0",
          fontSize: 13,
          color: "var(--muted, #6b7280)",
        }}
      >
        <span style={{ opacity: 0.8 }}>Retrieval skill:</span>
        {(["full", "lean"] as const).map((opt) => {
          const on = skill === opt;
          return (
            <button
              key={opt}
              type="button"
              role="radio"
              aria-checked={on}
              data-testid={`skill-${opt}`}
              onClick={() => setSkill(opt)}
              title={
                opt === "lean"
                  ? "Lean: slimmer skill prompt — cheaper & faster, same grounding/citations"
                  : "Full: thorough navigator — reads the processing references in full"
              }
              style={{
                cursor: "pointer",
                padding: "3px 12px",
                borderRadius: 999,
                border: "1px solid",
                borderColor: on ? "var(--accent, #b08d57)" : "rgba(0,0,0,0.18)",
                background: on ? "var(--accent, #b08d57)" : "transparent",
                color: on ? "#fff" : "inherit",
                fontWeight: on ? 600 : 400,
                textTransform: "capitalize",
                transition: "all .15s ease",
              }}
            >
              {opt}
            </button>
          );
        })}
        <span style={{ opacity: 0.6, fontSize: 12 }}>
          {skill === "lean" ? "slimmer prompt — cheaper" : "thorough navigator"}
        </span>
      </div>

      {/* Live upload: drop your own CSV/PDF/xlsx, then ask a question over them. The agent
          reads the uploaded files (per-session, isolated, read-only) the same way it reads the
          committed knowledge base — citing every claim to a file + page/row. */}
      <div className="upload-zone" data-testid="upload-zone">
        <div
          className={`dropzone${dragOver ? " over" : ""}${uploads.length ? " has-files" : ""}`}
          data-testid="dropzone"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files?.length) uploadFiles(e.dataTransfer.files);
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.pdf,.xlsx"
            multiple
            hidden
            data-testid="file-input"
            onChange={(e) => e.target.files && uploadFiles(e.target.files)}
          />
          {uploading ? (
            <span className="dz-line">
              <span className="spinner" /> Uploading &amp; preparing your files…
            </span>
          ) : (
            <span className="dz-line">
              <b>Upload your own data</b> — drop a CSV, PDF, or Excel file here (or click), then ask a
              question over it. Your files stay private to this session.
            </span>
          )}
        </div>

        {uploadError && (
          <p className="err" data-testid="upload-error">
            {uploadError}
          </p>
        )}

        {uploads.length > 0 && (
          <div className="uploaded-files" data-testid="uploaded-files">
            <div className="uf-head">
              <span>
                {uploads.length} file{uploads.length === 1 ? "" : "s"} ready — your next question is
                answered over {uploads.length === 1 ? "it" : "them"}.
              </span>
              <button className="uf-clear" onClick={clearUploads} data-testid="clear-uploads">
                clear
              </button>
            </div>
            <ul>
              {uploads.map((f) => (
                <li key={f.name} className={`uf ${f.kind}`} data-testid={`uploaded-${f.name}`}>
                  <span className="uf-name">{f.name}</span>
                  <span className="uf-meta">
                    {f.kind === "pdf"
                      ? `${f.pages ?? "?"} page${f.pages === 1 ? "" : "s"}`
                      : `${f.rows ?? "?"} rows · ${f.columns.length} cols`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {!result && !loading && !error && (
        <>
          <p className="examples-label">Try a capability</p>
          <div className="examples">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.q}
                className="example-card"
                style={{ ["--chip" as string]: ex.chip }}
                onClick={() => {
                  setQuestion(ex.q);
                  ask(ex.q);
                }}
              >
                <span className="feat">{ex.feat}</span>
                <span className="q" dir={isHebrew(ex.q) ? "rtl" : "ltr"}>
                  {ex.q}
                </span>
              </button>
            ))}
          </div>
          <p className="empty-hint">
            Every answer shows the agent&apos;s trace (which maps it read, which files it opened) and
            a chip for each fact — click a chip to jump to the source.
          </p>
        </>
      )}

      {error && (
        <div className="card error-card">
          <h2>Something went wrong</h2>
          <p className="err">{error}</p>
          <p className="muted" style={{ marginTop: 8 }}>
            Try again, or ask a different question.
          </p>
        </div>
      )}

      {loading && (
        <div className="card" data-testid="thinking-panel">
          <div className="thinking">
            <span className="spinner" />
            <span>
              The agent is navigating the knowledge base and retrieving evidence
              <span className="steps"> · navigate → learn → extract → self-check → cite</span>
            </span>
          </div>
          {liveTrace.length > 0 && (
            <ol className="trace-list live" data-testid="live-trace">
              {liveTrace.map((t, i) => (
                <li key={i} className={`trace-step ${t.kind}`}>
                  <span className="trace-kind">{t.kind}</span>
                  <span className="trace-detail">{t.detail}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {result && (
        <>
          <div className="card" data-testid="trace-panel">
            <h2>Agent trace</h2>
            <p className="rationale">
              The maps the agent read and the files it opened to answer — this is how you verify it
              did real retrieval (and never opened an unrelated domain).
            </p>
            <ol className="trace-list">
              {trace.map((t, i) => (
                <li key={i} className={`trace-step ${t.kind}`} data-testid={`trace-${t.kind}`}>
                  <span className="trace-kind">{t.kind}</span>
                  <span className="trace-detail">{t.detail}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="card">
            <h2>Answer</h2>
            <div
              className="answer"
              data-testid="answer"
              dir={answerRtl ? "rtl" : "ltr"}
              lang={answerRtl ? "he" : "en"}
            >
              {renderAnswer(result.answer)}
            </div>
            <div
              className={`validation ${result.validation.ok ? "ok" : "bad"}`}
              data-testid="validation"
            >
              <span className="mk">{result.validation.ok ? "✓" : "✗"}</span>
              <span>
                {result.validation.ok
                  ? "Grounded — every cited source resolves to a real file + page/row (validateAnswer passed)."
                  : "Rejected by validateAnswer(): " + result.validation.reasons.join("; ")}
              </span>
            </div>
          </div>

          <div className="card" data-testid="sources-panel" ref={sourcesRef}>
            <h2>
              Sources — {evidence.length} cited{" "}
              {evidence.length === 1 ? "source" : "sources"}
            </h2>

            {evidence.length === 0 && (
              <p className="muted" style={{ fontStyle: "italic" }}>
                No sources were cited for this question — which is why the answer states what it
                cannot determine rather than guessing.
              </p>
            )}

            {evidence.map((e) => {
              const token = `[F:${e.file}#${e.loc}]`;
              const pdf = isPdfFile(e.file);
              return (
                <div
                  className={`evidence-row${activeCite === token ? " highlight" : ""}`}
                  key={token}
                  id={`src-${cssId(token)}`}
                >
                  <span className={`tok ${pdf ? "pdf" : "sql"}`}>
                    [{fileLabel(e.file)}#{e.loc}]
                  </span>
                  <div className="evidence-body">
                    <div className="meta">
                      {e.file} · {locLabel(e.loc)}
                    </div>
                    <span className="data" dir={isHebrew(e.snippet) ? "rtl" : "ltr"}>
                      {e.snippet.slice(0, 240)}
                      {e.snippet.length > 240 ? "…" : ""}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <button
            className="more"
            style={{ marginTop: 18 }}
            onClick={() => {
              setResult(null);
              setQuestion("");
            }}
          >
            ← Ask another question
          </button>
        </>
      )}

      <footer className="foot">
        <span>Aletheia · agentic knowledge assistant</span>
        <span className="sep">·</span>
        <a
          href="https://github.com/qufeiz/Contract-Retriever-Agentic"
          target="_blank"
          rel="noreferrer"
        >
          source
        </a>
        <span className="sep">·</span>
        <span>navigate · read real files · cited &amp; verified</span>
      </footer>
    </div>
  );
}

// Stable DOM id from a citation token (so chips can scroll to their source row).
function cssId(token: string) {
  return token.replace(/[^a-zA-Z0-9]+/g, "-");
}
