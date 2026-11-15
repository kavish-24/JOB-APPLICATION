import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import { Alert, CardHead, EmptyState, Icon, PageHead, Stat } from "../components.jsx";
import { navigate } from "../router.js";

const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "–");
const keyOf = (s) => s.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

function SectionInfo({ s }) {
  const where = s.found_by === "inline" ? "an inline “Skills:” line" : `“${s.heading}”`;
  return (
    <div className="info-row">
      <Icon name="target" className="sm" />
      <span>Skills section: {where} · page {s.page} · {s.lines} line{s.lines > 1 ? "s" : ""} · {s.font}</span>
    </div>
  );
}

function UploadError({ message }) {
  return (
    <Alert tone="coral" icon="error" title="Couldn't use this PDF">
      <p>{message}</p>
      {/skills section|skills heading/i.test(message) && (
        <ol>
          <li>Make sure it's a text PDF (you can select the text), not a scanned image.</li>
          <li>Give the skills a clear heading such as “Skills” or “Technical Skills”.</li>
          <li>List skills as text, e.g. “Languages: Python, Java” or “Python, Java, SQL”.</li>
        </ol>
      )}
    </Alert>
  );
}

function UploadForm({ existing, onDone }) {
  const [category, setCategory] = useState("");
  const [file, setFile] = useState(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);
  const match = existing.find((r) => r.label.toLowerCase() === category.trim().toLowerCase()
    || (category.trim() && r.key === keyOf(category)));

  const pick = (f) => {
    if (!f) return;
    if (!/\.pdf$/i.test(f.name)) return setError("That file is not a PDF");
    setError("");
    setFile(f);
  };

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
      <CardHead eyebrow="New base resume" title={<>Add a resume category<span className="dot-accent">.</span></>} />
      <label className="field"><span>Category name</span>
        <input value={category} onChange={(e) => setCategory(e.target.value)}
               placeholder="e.g. Test Engineer, Data Analyst, DevOps Engineer…" list="known-categories" />
        <datalist id="known-categories">
          {existing.map((r) => <option key={r.key} value={r.label} />)}
        </datalist>
      </label>
      <div className={`dropzone ${over ? "over" : ""}`} role="button" tabIndex={0}
           onClick={() => fileRef.current?.click()}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), fileRef.current?.click())}
           onDragOver={(e) => { e.preventDefault(); setOver(true); }}
           onDragLeave={() => setOver(false)}
           onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files?.[0]); }}>
        <span className="icon-circle"><Icon name="cloud_upload" /></span>
        {file
          ? <span className="picked"><Icon name="picture_as_pdf" className="sm" /> {file.name}</span>
          : <span>Drop your resume PDF here, or <span className="browse">browse</span></span>}
        <span className="faint small mono">text PDFs up to 10 MB</span>
        <input ref={fileRef} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => pick(e.target.files?.[0])} />
      </div>
      <div className="info-row">
        <Icon name="info" className="sm" />
        <span>crafter finds the skills section (“Skills”, “Technical Skills”, “Core Competencies”…) and remembers where each line sits, so it can add skills there later without touching the rest.</span>
      </div>
      {result && (
        <Alert tone="lime" icon="check_circle" title={`Saved “${result.label}” · ${result.total_skills} skills found`}>
          <p>Skills section: {result.skills_section.found_by === "inline" ? "inline “Skills:” line" : `“${result.skills_section.heading}”`} · page {result.skills_section.page} · {result.skills_section.lines} lines · {result.skills_section.font}</p>
        </Alert>
      )}
      {error && <UploadError message={error} />}
      <div className="row end">
        <button className="btn primary" disabled={busy}>
          {busy ? <><span className="spin" /> Reading resume…</>
            : <>{match ? `Replace '${match.label}'` : "Add category"}<Icon name="arrow_forward" className="sm" /></>}
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
          <h2>{r.label}<span className="led" /></h2>
          <p className="sub">Uploaded {fmt(r.uploaded_at)} · PDF master</p>
        </div>
        <span className="badge lime">{r.total_skills} skills</span>
      </div>
      <div className="file-row"><Icon name="description" className="sm" /><span>{r.file}</span></div>
      <SectionInfo s={r.skills_section} />
      <div className="resume-actions">
        <a className="btn ghost sm" href={r.url} target="_blank" rel="noreferrer">View <Icon name="north_east" className="sm" /></a>
        <button type="button" className="btn ghost sm" onClick={() => replaceRef.current?.click()}>Replace PDF</button>
        <input ref={replaceRef} type="file" accept="application/pdf,.pdf" hidden
               onChange={(e) => replace(e.target.files?.[0])} />
        <button type="button" className="btn ghost sm" onClick={rename}>Rename</button>
        <button type="button" className="btn ghost sm" onClick={() => setShowSkills(!showSkills)} aria-expanded={showSkills}>
          {showSkills ? "Hide skills" : "Skills"}
        </button>
        <button type="button" className="btn danger sm push" onClick={remove}>Remove</button>
      </div>
      {error && <UploadError message={error} />}
      {showSkills && (
        <div className="table">
          {r.category_order.map((cat) => (
            <div className="tr space" key={cat}>
              <span className="faint small mono">{cat}</span>
              <span className="small">{r.skills[cat].join(", ")}</span>
            </div>
          ))}
        </div>
      )}
      {r.previous_versions.length > 0 ? (
        <details className="versions">
          <summary>{r.previous_versions.length} previous version{r.previous_versions.length > 1 ? "s" : ""}</summary>
          {r.previous_versions.map((v) => (
            <a key={v} className="link" href={`/api/resumes/${r.key}/versions/${encodeURIComponent(v)}`}
               target="_blank" rel="noreferrer">{v} ↗</a>
          ))}
        </details>
      ) : <span className="versions">Initial base version</span>}
    </article>
  );
}

function SkillsCard({ data }) {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState("all");
  const total = data.resumes.length;
  const labelOf = useMemo(() => Object.fromEntries(data.resumes.map((r) => [r.key, r.label])), [data]);
  const skills = data.skills.filter((s) => (tab === "all" || s.tags.includes(tab))
    && s.skill.toLowerCase().includes(query.toLowerCase()));
  const universal = total > 1 ? skills.filter((s) => s.tags.length === total) : [];
  const specific = total > 1 ? skills.filter((s) => s.tags.length < total) : skills;

  return (
    <section className="card">
      <CardHead title="Skills you have" sub={`Extracted from all ${total} base resume${total === 1 ? "" : "s"}.`}>
        <label className="search-box" style={{ minWidth: 240 }}>
          <Icon name="search" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Filter ${data.skills.length} skills…`}
                 aria-label="Filter skills" />
        </label>
      </CardHead>
      {total > 1 && (
        <div className="tabs" role="tablist" aria-label="Resume category">
          <button type="button" role="tab" aria-selected={tab === "all"} className={tab === "all" ? "on" : ""}
                  onClick={() => setTab("all")}>All ({data.skills.length})</button>
          {data.resumes.map((r) => (
            <button key={r.key} type="button" role="tab" aria-selected={tab === r.key} className={tab === r.key ? "on" : ""}
                    onClick={() => setTab(r.key)}>{r.label} ({data.skills.filter((s) => s.tags.includes(r.key)).length})</button>
          ))}
        </div>
      )}
      <div className="skill-groups">
        {universal.length > 0 && (
          <div>
            <h4>Universal skills · on all {total} resumes</h4>
            <div className="chips">{universal.map((s) => <span key={s.skill} className="chip lime"><span className="led" />{s.skill}</span>)}</div>
          </div>
        )}
        <div>
          {total > 1 && <h4>{universal.length ? "Category-specific skills" : "Skills"}</h4>}
          <div className="chips">
            {specific.map((s) => (
              <span key={s.skill} className="chip" title={`In: ${s.tags.map((t) => labelOf[t] || t).join(", ")}`}>
                {s.skill}
                {total > 1 && <span className="tagl">{s.tags.map((t) => labelOf[t] || t).join(", ")}</span>}
              </span>
            ))}
            {!specific.length && !universal.length && <span className="faint small">Nothing matches.</span>}
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Profile() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = () => api.get("/api/profile").then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  if (!data) return error ? <p className="error">{error}</p> : <p className="faint">Loading…</p>;
  const j = data.jobs;
  const u = data.user || {};

  return (
    <>
      <PageHead eyebrow="Settings & inventory · candidate profile" title="Your profile"
                lede={<>{u.name ? <>Candidate <b style={{ color: "var(--text)" }}>{u.name}</b>{u.email && <> (<span className="lime mono">{u.email}</span>)</>} · </> : null}
                  A base resume for every role you're going after, the skills they list, and how your applications are going.</>}>
        <span className="pill"><span className="led lime" />{data.resumes.length} categories indexed</span>
      </PageHead>

      <div className="stats">
        <Stat label="Resume categories" value={data.resumes.length} unit="active" />
        <Stat label="Unique skills" value={data.skills.length} unit="indexed" />
        <Stat label="Applications" value={j.total} unit="sent" onClick={() => navigate("/job_hunt")} />
        <Stat label="Interviewing" value={j.interviewing} unit="active" tone="amber" />
        <Stat label="Cleared" value={j.cleared} unit="offers" tone="lime" />
        <Stat label="Rejected" value={j.rejected} unit="archived" tone="coral" />
      </div>

      <div className="list-title" style={{ marginTop: 28 }}>
        <div>
          <h2>Resume categories</h2>
          <p className="muted small" style={{ margin: "2px 0 0" }}>Base resumes parsed by crafter's skills-section finder.</p>
        </div>
        <span className="count-note">{data.resumes.length} loaded</span>
      </div>
      {data.resumes.length === 0 ? (
        <div style={{ marginBottom: 26 }}>
          <EmptyState icon="note_add" title="No base resumes yet">Add one below: name the role, upload the PDF.</EmptyState>
        </div>
      ) : (
        <div className="resume-grid">
          {data.resumes.map((r) => <ResumeCard key={r.key} r={r} onChanged={load} />)}
        </div>
      )}

      <UploadForm existing={data.resumes} onDone={load} />
      {data.skills.length > 0 && <SkillsCard data={data} />}
    </>
  );
}
