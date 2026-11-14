import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Segmented, Stat, TagInput } from "../components.jsx";
import { navigate } from "../router.js";

export const STAGES = [
  { value: "applied", label: "Applied", tone: "zinc" },
  { value: "interviewing", label: "Interviewing", tone: "amber" },
  { value: "cleared", label: "Cleared", tone: "lime" },
  { value: "rejected", label: "Rejected", tone: "coral" },
];
export const TONE = Object.fromEntries(STAGES.map((s) => [s.value, s.tone]));
const today = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD, local

export function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - date) / 86400000);
  const ago = days <= 0 ? "today" : days === 1 ? "yesterday" : `${days}d ago`;
  return { label: date.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }), ago };
}

const EMPTY = { company: "", role: "", link: "", resume_used: "", skills_lacking: [],
                applied_date: today(), stage: "applied", notes: "" };

function AddForm({ initial, resumes, onSaved, onCancel }) {
  const [f, setF] = useState(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((p) => ({ ...p, [k]: v?.target ? v.target.value : v }));
  const options = useMemo(() => {
    const names = resumes.map((r) => r.file);
    return f.resume_used && !names.includes(f.resume_used) ? [f.resume_used, ...names] : names;
  }, [resumes, f.resume_used]);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body = { ...f, link: f.link || null, resume_used: f.resume_used || null, notes: f.notes || null };
      onSaved(await api.post("/api/job_hunt", body));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <div className="card-head">
        <div><p className="eyebrow">New</p><h2>Add an application</h2></div>
      </div>
      <div className="field-row">
        <label className="field grow"><span>Company</span>
          <input required value={f.company} onChange={set("company")} placeholder="Acme Labs" autoFocus />
        </label>
        <label className="field grow"><span>Role</span>
          <input required value={f.role} onChange={set("role")} placeholder="AI Engineer – Fresher" />
        </label>
      </div>
      <div className="field-row">
        <label className="field grow"><span>Job link</span>
          <input type="url" value={f.link} onChange={set("link")} placeholder="https://…" />
        </label>
        <label className="field"><span>Applied on</span>
          <input type="date" value={f.applied_date} onChange={set("applied_date")} />
        </label>
      </div>
      <label className="field"><span>Resume used</span>
        <select value={f.resume_used} onChange={set("resume_used")}>
          <option value="">— none —</option>
          {options.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </label>
      <label className="field"><span>Stage</span>
        <Segmented name="Stage" options={STAGES} value={f.stage} onChange={set("stage")} />
      </label>
      <label className="field"><span>Skills I lack (study these if shortlisted)</span>
        <TagInput value={f.skills_lacking} onChange={set("skills_lacking")} />
      </label>
      <label className="field"><span>Notes</span>
        <textarea className="short" value={f.notes} onChange={set("notes")} placeholder="Referral, recruiter name, round details…" />
      </label>
      <div className="row end">
        {error && <p className="error">{error}</p>}
        <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
        <button className="btn primary" disabled={saving}>{saving ? "Saving…" : "Save application"}</button>
      </div>
    </form>
  );
}

function JobRow({ job, onChange }) {
  const { label, ago } = fmtDate(job.applied_date);
  const patch = async (body) => {
    try { onChange(await api.patch(`/api/job_hunt/${job.id}`, body)); } catch { /* shown on detail page */ }
  };
  const shown = job.skills_lacking.slice(0, 4);
  const more = job.skills_lacking.length - shown.length;
  const open = () => navigate(`/job_hunt/${job.id}`);

  return (
    <article className="job">
      <div className="job-main" role="link" tabIndex={0} onClick={open}
           onKeyDown={(e) => e.key === "Enter" && open()}>
        <span className={`dot ${TONE[job.stage]}`} aria-hidden="true" />
        <div className="job-title">
          <span className="strong">{job.company}</span>
          <span className="muted">{job.role}</span>
        </div>
        <div className="job-skills">
          {shown.map((s) => <span key={s} className="chip">{s}</span>)}
          {more > 0 && <span className="chip faint">+{more}</span>}
        </div>
        <div className="job-date mono">
          <span>{label}</span><span className="faint">{ago}</span>
        </div>
        <select className={`stage-select ${TONE[job.stage]}`} value={job.stage}
                onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}
                onChange={(e) => patch({ stage: e.target.value })} aria-label="Stage">
          {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>
    </article>
  );
}

export default function JobHunt() {
  const [jobs, setJobs] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [form, setForm] = useState(null); // initial values when the add form is open
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/job_hunt").then((d) => setJobs(d.jobs)).catch((e) => setError(e.message));
    api.get("/outputs").then(setResumes).catch(() => {});
    const pre = sessionStorage.getItem("prefill");
    if (pre) {
      sessionStorage.removeItem("prefill");
      try { setForm({ ...EMPTY, ...JSON.parse(pre) }); } catch { /* ignore bad prefill */ }
    }
  }, []);

  const counts = useMemo(() => {
    const c = { all: jobs?.length ?? 0 };
    for (const s of STAGES) c[s.value] = jobs?.filter((j) => j.stage === s.value).length ?? 0;
    return c;
  }, [jobs]);

  // what to study: skills lacking across jobs where you are interviewing
  const study = useMemo(() => {
    const tally = new Map();
    for (const j of jobs || [])
      if (j.stage === "interviewing")
        for (const s of j.skills_lacking) tally.set(s, (tally.get(s) || 0) + 1);
    return [...tally.entries()].sort((a, b) => b[1] - a[1]);
  }, [jobs]);

  const shown = (jobs || []).filter((j) =>
    (filter === "all" || j.stage === filter) &&
    `${j.company} ${j.role} ${j.skills_lacking.join(" ")}`.toLowerCase().includes(query.toLowerCase()));

  const replace = (item) => setJobs((js) => js.map((j) => (j.id === item.id ? item : j)));

  return (
    <>
      <section className="hero row between">
        <div>
          <p className="eyebrow">Step 2</p>
          <h1>Job hunt<span className="lime">.</span></h1>
          <p className="muted">Every application, the resume you sent, and what to study if they call back.</p>
        </div>
        {!form && <button type="button" className="btn primary" onClick={() => setForm(EMPTY)}>+ New application</button>}
      </section>

      <div className="stats">
        <Stat value={counts.all} label="total" active={filter === "all"} onClick={() => setFilter("all")} />
        {STAGES.map((s) => (
          <Stat key={s.value} value={counts[s.value]} label={s.label.toLowerCase()} tone={s.tone}
                active={filter === s.value} onClick={() => setFilter(s.value)} />
        ))}
      </div>

      {form && (
        <AddForm initial={form} resumes={resumes} onCancel={() => setForm(null)}
                 onSaved={(item) => { setJobs((js) => [item, ...(js || [])]); setForm(null); }} />
      )}

      <section className="card study">
        <div className="card-head">
          <div><p className="eyebrow">Study queue</p>
            <h2>{study.length ? "Learn these before your interviews" : "Nothing to study yet"}</h2></div>
        </div>
        {study.length ? (
          <div className="chips">
            {study.map(([s, n]) => (
              <span key={s} className="chip amber">{s}{n > 1 && <b className="count">×{n}</b>}</span>
            ))}
          </div>
        ) : (
          <p className="faint">When an application moves to <b>interviewing</b>, its skills you lack show up here.</p>
        )}
      </section>

      <section className="list">
        <div className="row between list-head">
          <h3>{filter === "all" ? "All applications" : STAGES.find((s) => s.value === filter).label}</h3>
          <input className="search" value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder="Search company, role, skill" aria-label="Search applications" />
        </div>
        {error && <p className="error">{error}</p>}
        {jobs === null && !error && <p className="faint">Loading…</p>}
        {jobs?.length === 0 && (
          <div className="empty">
            <p className="strong">No applications yet.</p>
            <p className="faint">Tailor a resume, then hit <b>Track application</b>, or add one by hand.</p>
          </div>
        )}
        {jobs?.length > 0 && shown.length === 0 && <p className="faint">Nothing matches.</p>}
        {shown.map((j) => <JobRow key={j.id} job={j} onChange={replace} />)}
      </section>
    </>
  );
}
