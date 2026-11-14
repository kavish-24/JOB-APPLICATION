import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import { Stat } from "../components.jsx";
import { navigate } from "../router.js";

const STAGE_TONE = { applied: "", interviewing: "amber", cleared: "lime", rejected: "coral" };
const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "–");

function SectionInfo({ s }) {
  const where = s.found_by === "inline" ? "an inline “Skills:” line" : `“${s.heading}”`;
  return (
    <p className="muted small section-info">
      Skills section: {where} · page {s.page} · {s.lines} line{s.lines > 1 ? "s" : ""} · {s.font}
    </p>
  );
}

function UploadForm({ existing, onDone }) {
  const [category, setCategory] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);
  const match = existing.find((r) => r.label.toLowerCase() === category.trim().toLowerCase()
    || r.key === category.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""));

  async function submit(e) {
    e.preventDefault();
    if (!category.trim() || !file) return setError("Name the category and choose a PDF.");
    if (match && !window.confirm(`Replace the '${match.label}' base resume? The current PDF is kept as a previous version.`)) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", category.trim());
      setResult(await api.upload("/api/resumes", fd));
      setCategory(""); setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <div className="card-head">
        <div><p className="eyebrow">Base resume</p><h2>Add a resume category</h2></div>
      </div>
      <div className="field-row">
        <label className="field grow"><span>Category</span>
          <input value={category} onChange={(e) => setCategory(e.target.value)}
                 placeholder="Test Engineer, Data Analyst, DevOps…" list="known-categories" />
          <datalist id="known-categories">
            {existing.map((r) => <option key={r.key} value={r.label} />)}
          </datalist>
        </label>
        <label className="field grow"><span>Resume PDF</span>
          <input ref={fileRef} type="file" accept="application/pdf,.pdf"
                 onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
      </div>
      <p className="faint small">
        Crafter finds the skills section (“Skills”, “Technical Skills”, “Core Competencies”…) and remembers
        exactly where each line sits, so it can add skills there later without touching the rest.
      </p>
      {result && (
        <div className="notice">
          <b>Saved “{result.label}”.</b> Found {result.total_skills} skills.
          <SectionInfo s={result.skills_section} />
        </div>
      )}
      <div className="row end">
        {error && <p className="error">{error}</p>}
        <button className="btn primary" disabled={busy}>
          {busy ? <><span className="spin" /> Reading resume…</> : match ? `Replace '${match.label}'` : "Add category"}
        </button>
      </div>
    </form>
  );
}

function ResumeCard({ r, onChanged }) {
  const [error, setError] = useState("");
  const [showSkills, setShowSkills] = useState(false);
  const replaceRef = useRef(null);

  const rename = async () => {
    const label = window.prompt("Category name", r.label);
    if (!label || label.trim() === r.label) return;
    setError("");
    try { await api.patch(`/api/resumes/${r.key}`, { label: label.trim() }); onChanged(); }
    catch (err) { setError(err.message); }
  };
  const replace = async (file) => {
    if (!file) return;
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", r.label);
      await api.upload("/api/resumes", fd);
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      if (replaceRef.current) replaceRef.current.value = "";
    }
  };
  const remove = async () => {
    if (!window.confirm(`Remove the '${r.label}' category? Its PDF is moved to resume/_deleted, not erased.`)) return;
    try { await api.del(`/api/resumes/${r.key}`); onChanged(); }
    catch (err) { setError(err.message); }
  };

  return (
    <article className="card resume-card">
      <div className="card-head">
        <div>
          <p className="eyebrow">Uploaded {fmt(r.uploaded_at)}</p>
          <h2>{r.label}</h2>
          <p className="faint small mono">{r.file}</p>
        </div>
        <span className="badge lime">{r.total_skills} skills</span>
      </div>
      <SectionInfo s={r.skills_section} />
      <div className="row resume-actions">
        <a className="btn ghost sm" href={r.url} target="_blank" rel="noreferrer">View ↗</a>
        <button type="button" className="btn ghost sm" onClick={() => replaceRef.current?.click()}>Replace PDF</button>
        <input ref={replaceRef} type="file" accept="application/pdf,.pdf" hidden
               onChange={(e) => replace(e.target.files?.[0])} />
        <button type="button" className="btn ghost sm" onClick={rename}>Rename</button>
        <button type="button" className="btn ghost sm" onClick={() => setShowSkills(!showSkills)}>
          {showSkills ? "Hide skills" : "Skills"}
        </button>
        <button type="button" className="btn danger sm" onClick={remove}>Remove</button>
      </div>
      {error && <p className="error">{error}</p>}
      {showSkills && (
        <div className="table">
          {r.category_order.map((cat) => (
            <div className="tr space" key={cat}>
              <span className="faint">{cat}</span>
              <span className="small" style={{ gridColumn: "span 2" }}>{r.skills[cat].join(", ")}</span>
            </div>
          ))}
        </div>
      )}
      {r.previous_versions.length > 0 && (
        <details className="versions">
          <summary className="faint small">{r.previous_versions.length} previous version{r.previous_versions.length > 1 ? "s" : ""}</summary>
          {r.previous_versions.map((v) => (
            <a key={v} className="link small" href={`/api/resumes/${r.key}/versions/${encodeURIComponent(v)}`}
               target="_blank" rel="noreferrer">{v} ↗</a>
          ))}
        </details>
      )}
    </article>
  );
}

export default function Profile() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  const load = () => api.get("/api/profile").then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const skills = useMemo(() => (data?.skills || []).filter((s) =>
    s.skill.toLowerCase().includes(query.toLowerCase())), [data, query]);
  const labelOf = useMemo(() => Object.fromEntries((data?.resumes || []).map((r) => [r.key, r.label])), [data]);

  if (!data) return error ? <p className="error">{error}</p> : <p className="faint">Loading…</p>;
  const j = data.jobs;
  const many = data.resumes.length > 1;

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Profile</p>
        <h1>Your profile<span className="lime">.</span></h1>
        <p className="muted">A base resume for every role you're going after, the skills they list, and how your applications are going.</p>
      </section>

      <div className="stats">
        <Stat value={data.resumes.length} label="resume categories" tone="lime" />
        <Stat value={data.skills.length} label="unique skills" />
        <Stat value={j.total} label="applications" onClick={() => navigate("/job_hunt")} />
        {["applied", "interviewing", "cleared", "rejected"].map((s) => (
          <Stat key={s} value={j[s]} label={s} tone={STAGE_TONE[s]} />
        ))}
      </div>

      <h3>Resume categories</h3>
      {data.resumes.length === 0 && (
        <div className="empty"><p className="strong">No base resumes yet.</p>
          <p className="faint">Add one below: name the role, upload the PDF.</p></div>
      )}
      <div className="resume-grid">
        {data.resumes.map((r) => <ResumeCard key={r.key} r={r} onChanged={load} />)}
      </div>

      <UploadForm existing={data.resumes} onDone={load} />

      <section className="card">
        <div className="card-head">
          <div><p className="eyebrow">Skills you have</p><h2>{data.skills.length} skills across your resumes</h2></div>
          <input className="search" value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder="Search skills" aria-label="Search skills" />
        </div>
        <div className="chips">
          {skills.map((s) => (
            <span key={s.skill} className={`chip ${many && s.tags.length === data.resumes.length ? "lime" : ""}`}
                  title={`In: ${s.tags.map((t) => labelOf[t] || t).join(", ")}`}>
              {s.skill}
              {many && s.tags.length < data.resumes.length &&
                <span className="faint"> · {s.tags.map((t) => labelOf[t] || t).join(", ")}</span>}
            </span>
          ))}
          {!skills.length && <span className="faint">Nothing matches.</span>}
        </div>
        {many && <p className="faint small">Green = on every resume; others show which categories list them.</p>}
      </section>
    </>
  );
}
