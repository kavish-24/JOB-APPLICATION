import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { CardHead, EmptyState, Icon, PageHead, Segmented, Stat, TagInput } from "../components.jsx";
import { navigate } from "../router.js";

export const STAGES = [
  { value: "applied", label: "Applied", tone: "lime", unit: "awaiting", icon: "radio_button_checked" },
  { value: "interviewing", label: "Interviewing", tone: "amber", unit: "active rounds", icon: "forum" },
  { value: "cleared", label: "Cleared", tone: "lime", unit: "offers", icon: "verified" },
  { value: "rejected", label: "Rejected", tone: "coral", unit: "archived", icon: "close" },
];
export const TONE = { applied: "zinc", interviewing: "amber", cleared: "lime", rejected: "coral" };
const today = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD, local
const SORTS = {
  recent: { label: "Recent first", fn: (a, b) => (b.applied_date + b.created_at).localeCompare(a.applied_date + a.created_at) },
  oldest: { label: "Oldest first", fn: (a, b) => (a.applied_date + a.created_at).localeCompare(b.applied_date + b.created_at) },
  company: { label: "Company A–Z", fn: (a, b) => a.company.localeCompare(b.company) },
};

export function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - date) / 86400000);
  const ago = days <= 0 ? "today" : days === 1 ? "yesterday" : days < 14 ? `${days}d ago` : `${Math.round(days / 7)}w ago`;
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
      <CardHead eyebrow="New · manual entry" title="Add an application" />
      <div className="field-row">
        <label className="field"><span>Company</span>
          <input required value={f.company} onChange={set("company")} placeholder="Razorpay" autoFocus />
        </label>
        <label className="field"><span>Role</span>
          <input required value={f.role} onChange={set("role")} placeholder="SDE-1 (Platform)" />
        </label>
      </div>
      <div className="field-row">
        <label className="field"><span>Job link <span className="faint">optional</span></span>
          <input type="url" value={f.link} onChange={set("link")} placeholder="https://…" />
        </label>
        <label className="field fixed"><span>Applied on</span>
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
        <Segmented name="Stage" options={STAGES.map((s) => ({ ...s, tone: s.tone === "lime" ? "" : s.tone }))}
                   value={f.stage} onChange={set("stage")} />
      </label>
      <label className="field"><span>Skills I lack <span className="faint">study these if shortlisted</span></span>
        <TagInput value={f.skills_lacking} onChange={set("skills_lacking")} />
      </label>
      <label className="field"><span>Notes</span>
        <textarea className="short prose" value={f.notes} onChange={set("notes")} placeholder="Referral, recruiter name, round details…" />
      </label>
      <div className="card-foot">
        <span className="hint"><Icon name="info" className="sm" />Tailored applications are saved from step 5 of Tailor</span>
        <div className="row">
          {error && <p className="error">{error}</p>}
          <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
          <button className="btn primary" disabled={saving}>{saving ? "Saving…" : "Save application"}</button>
        </div>
      </div>
    </form>
  );
}

function JobRow({ job, onChange }) {
  const { ago } = fmtDate(job.applied_date);
  const patch = async (body) => {
    try { onChange(await api.patch(`/api/job_hunt/${job.id}`, body)); } catch { /* shown on detail page */ }
  };
  const skills = [...(job.skills_added || []), ...(job.skills_matched || [])];
  const list = skills.length ? skills : job.skills_lacking;
  const shown = list.slice(0, 4);
  const more = list.length - shown.length;
  const note = (job.notes || "").split("\n")[0].slice(0, 60);
  const open = () => navigate(`/job_hunt/${job.id}`);

  return (
    <article className="job-row" role="link" tabIndex={0} onClick={open}
             onKeyDown={(e) => e.key === "Enter" && open()} aria-label={`${job.company}, ${job.role}`}>
      <span className={`dot ${TONE[job.stage]}`} aria-hidden="true" />
      <div className="who">
        <div className="line1">
          <span className="company">{job.company}</span>
          <span className="faint">·</span>
          <span className="role">{job.role}</span>
        </div>
        <div className="meta">Applied {ago}{note && <> · <span className="note">{note}</span></>}</div>
      </div>
      <div className="skills">
        {shown.map((s) => <span key={s} className="chip">{s}</span>)}
        {more > 0 && <span className="chip faint">+{more}</span>}
      </div>
      <select className={`stage-select ${TONE[job.stage]}`} value={job.stage}
              onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}
              onChange={(e) => patch({ stage: e.target.value })} aria-label="Stage">
        {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>
      <Icon name="arrow_forward" className="arrow" />
    </article>
  );
}

export default function JobHunt() {
  const [jobs, setJobs] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("recent");
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

  const q = query.toLowerCase();
  const shown = (jobs || []).filter((j) =>
    (filter === "all" || j.stage === filter) &&
    [j.company, j.role, ...j.skills_lacking, ...(j.skills_added || []), ...(j.skills_matched || [])]
      .join(" ").toLowerCase().includes(q)).sort(SORTS[sort].fn);

  const replace = (item) => setJobs((js) => js.map((j) => (j.id === item.id ? item : j)));

  return (
    <>
      <PageHead eyebrow="Application tracker // active pipeline" title="Job hunt"
                lede="Every application, the resume you sent, and what to study if they call back.">
        {!form && (
          <button type="button" className="btn primary" onClick={() => setForm(EMPTY)}>
            <Icon name="add" className="sm" />New application
          </button>
        )}
      </PageHead>

      <div className="stats">
        <Stat label="Total" value={counts.all} unit="records" active={filter === "all"} onClick={() => setFilter("all")}
              corner={<span className="all">ALL</span>} />
        {STAGES.map((s) => (
          <Stat key={s.value} label={s.label} value={counts[s.value]} unit={s.unit} icon={s.icon} tone={s.tone}
                active={filter === s.value} onClick={() => setFilter(filter === s.value ? "all" : s.value)} />
        ))}
      </div>

      {form && (
        <AddForm initial={form} resumes={resumes} onCancel={() => setForm(null)}
                 onSaved={(item) => { setJobs((js) => [item, ...(js || [])]); setForm(null); }} />
      )}

      <section className="card study">
        <CardHead eyebrow={<span className="amber" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                    <Icon name="bolt" className="sm" />Interview prep queue</span>}
                  title="Study queue"
                  sub="Skills you lack across applications that are in interviews.">
          {study.length > 0 && <span className="pill"><span className="led amber" />{study.length} topics queued</span>}
        </CardHead>
        {study.length ? (
          <div className="chips">
            {study.map(([s, n]) => (
              <span key={s} className="chip amber">{s}{n > 1 && <span className="count">×{n}</span>}</span>
            ))}
          </div>
        ) : (
          <p className="faint small" style={{ margin: 0 }}>When an application moves to <b className="amber">interviewing</b>, its skills you lack show up here.</p>
        )}
      </section>

      <div className="card toolbar">
        <label className="search-box">
          <Icon name="search" />
          <input value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder="Search by company, role or skill…" aria-label="Search applications" />
        </label>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort">
          {Object.entries(SORTS).map(([k, s]) => <option key={k} value={k}>{s.label}</option>)}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {jobs === null && !error && <p className="faint">Loading…</p>}
      {jobs?.length === 0 && !form && (
        <EmptyState icon="work_history" title="No applications tracked yet"
                    actions={<>
                      <button type="button" className="btn soft" onClick={() => setForm(EMPTY)}><Icon name="add" className="sm" />Add application manually</button>
                      <button type="button" className="btn primary" onClick={() => navigate("/")}>Go to Tailor <Icon name="arrow_forward" className="sm" /></button>
                    </>}>
          When you tailor a resume, click <b>Add to applied jobs</b> in step 5 to track rounds and study notes here.
        </EmptyState>
      )}
      {jobs?.length > 0 && shown.length === 0 && <p className="faint">Nothing matches.</p>}
      <div className="job-list">
        {shown.map((j) => <JobRow key={j.id} job={j} onChange={replace} />)}
      </div>
      {jobs?.length > 0 && (
        <div className="list-foot">
          <span><span className="lime">●</span> Showing {shown.length} of {jobs.length} applications</span>
        </div>
      )}
    </>
  );
}
