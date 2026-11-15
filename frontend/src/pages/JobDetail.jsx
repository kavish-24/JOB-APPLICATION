import { useEffect, useState } from "react";
import { api } from "../api.js";
import { CardHead, Chips, EmptyState, Icon, TagInput } from "../components.jsx";
import { navigate } from "../router.js";
import { STAGES, TONE, fmtDate } from "./JobHunt.jsx";

const back = (e) => { e.preventDefault(); navigate("/job_hunt"); };

function Crumbs({ job }) {
  return (
    <div className="crumbs">
      <nav aria-label="Breadcrumb">
        <a href="/job_hunt" onClick={back}><Icon name="arrow_back" className="sm" />All applications</a>
        {job && <>
          <span className="sep">/</span><span>{job.company}</span>
          <span className="sep">/</span><span className="here">{job.role}</span>
        </>}
      </nav>
    </div>
  );
}

export default function JobDetail({ id }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setJob(null);
    setError("");
    api.get(`/api/job_hunt/${id}`)
      .then((j) => { setJob(j); setNotes(j.notes || ""); })
      .catch((e) => setError(e.message));
  }, [id]);

  const patch = async (body) => {
    setError("");
    try { setJob(await api.patch(`/api/job_hunt/${id}`, body)); }
    catch (err) { setError(err.message); }
  };
  const remove = async () => {
    const files = [job.resume_used, job.cover_letter_file].filter(Boolean);
    const extra = files.length ? ` and its files (${files.join(", ")})` : "";
    if (!window.confirm(`Delete ${job.company} – ${job.role}${extra}? This can't be undone.`)) return;
    try { await api.del(`/api/job_hunt/${id}`); navigate("/job_hunt"); }
    catch (err) { setError(err.message); }
  };
  const copyLetter = () => {
    navigator.clipboard.writeText(job.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!job)
    return <><Crumbs />{error ? <p className="error">{error}</p> : <p className="faint">Loading…</p>}</>;

  const { label, ago } = fmtDate(job.applied_date);
  const history = [...(job.stage_history || [])].reverse();
  return (
    <>
      <Crumbs job={job} />
      <div className="detail-split">
        <div className="stack">
          {/* header */}
          <section className="card" style={{ margin: 0 }}>
            <div className="row between" style={{ alignItems: "flex-start" }}>
              <p className="eyebrow lime"><span className="led" />Applied {label} · {ago}</p>
              <select className={`stage-select ${TONE[job.stage]}`} value={job.stage}
                      onChange={(e) => patch({ stage: e.target.value })} aria-label="Stage">
                {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
            <h1 className="detail-title">{job.company}<span className="dot-accent">.</span></h1>
            <p className="detail-role">{job.role}</p>
            {job.link && (
              <div className="detail-links">
                <a className="link" href={job.link} target="_blank" rel="noreferrer">
                  <Icon name="link" className="sm" /> {job.link.replace(/^https?:\/\//, "")} ↗</a>
              </div>
            )}
            {error && <p className="error" style={{ marginTop: 10 }}>{error}</p>}
          </section>

          {/* skills */}
          <section className="card" style={{ margin: 0 }}>
            <CardHead eyebrow="Skill breakdown" title="What this application used" />
            <div className="group">
              <div className="group-head">
                <span className="label"><span className="led" />Added to the tailored resume</span>
                <span className="note">{(job.skills_added || []).length} added</span>
              </div>
              <Chips items={job.skills_added} tone="lime" icon="check" empty="nothing added (resume used as-is)" />
            </div>
            <div className="group">
              <div className="group-head">
                <span className="label"><span className="led zinc" />Already on your base resume</span>
                <span className="note">{(job.skills_matched || []).length} matched</span>
              </div>
              <Chips items={job.skills_matched} empty="not recorded" />
            </div>
            <div className="group">
              <div className="group-head">
                <span className="label"><span className="led amber" />Skills I lack — study if shortlisted</span>
                <span className="note">{job.skills_lacking.length} to review</span>
              </div>
              <TagInput value={job.skills_lacking} onChange={(v) => patch({ skills_lacking: v })} />
            </div>
          </section>

          {/* notes + timeline */}
          <section className="card" style={{ margin: 0 }}>
            <CardHead eyebrow="Interview notes & chronology" title="Notes">
              <span className="faint small mono">saved when you click away</span>
            </CardHead>
            <textarea className="short" value={notes} onChange={(e) => setNotes(e.target.value)}
                      onBlur={() => notes !== (job.notes || "") && patch({ notes: notes || null })}
                      placeholder="Referral, recruiter name, round details…" aria-label="Notes" />
            <h3>Timeline</h3>
            <ol className="timeline">
              {history.map((h, i) => (
                <li key={i}><span className={`dot ${TONE[h.stage]}`} />
                  <span className="when">{h.at.replace("T", " ").slice(0, 16)}</span>{h.stage}</li>
              ))}
            </ol>
          </section>

          {/* cover letter */}
          {job.cover_letter && (
            <section className="card" style={{ margin: 0 }}>
              <CardHead eyebrow="Attached cover letter" title="Cover letter">
                <button type="button" className="btn ghost sm" onClick={copyLetter}>
                  <Icon name={copied ? "check" : "content_copy"} className="sm" />{copied ? "Copied" : "Copy letter"}</button>
                {job.cover_letter_file && (
                  <a className="btn ghost sm" href={`/files/${job.cover_letter_file}`} target="_blank" rel="noreferrer">
                    <Icon name="download" className="sm" />PDF</a>
                )}
              </CardHead>
              <p className="letter-block">{job.cover_letter}</p>
            </section>
          )}

          {job.jd && (
            <details className="card jd-block" style={{ margin: 0 }}>
              <summary>
                <span className="row"><Icon name="description" className="sm lime" />Original job description</span>
                <Icon name="expand_more" className="faint" />
              </summary>
              <p className="jd-text">{job.jd}</p>
            </details>
          )}

          <section className="danger-zone">
            <h2>Danger zone</h2>
            <p>Permanently delete this application{job.resume_used || job.cover_letter_file ? " and the resume copy / cover letter made for it" : ""}.</p>
            <button type="button" className="btn danger" onClick={remove}><Icon name="delete" className="sm" />Delete application</button>
          </section>
        </div>

        <aside className="card doc-pane">
          {job.resume_used ? (
            <>
              <div className="doc-bar">
                <span className="file"><Icon name="picture_as_pdf" className="sm lime" />{job.resume_used}</span>
                <span className="row">
                  <a className="btn ghost icon" href={`/files/${job.resume_used}`} target="_blank" rel="noreferrer"
                     title="Open in a new tab" aria-label="Open in a new tab"><Icon name="open_in_new" className="sm" /></a>
                  <a className="btn soft sm" href={`/files/${job.resume_used}`} download><Icon name="download" className="sm" />PDF</a>
                </span>
              </div>
              <iframe title="Resume sent" src={`/files/${job.resume_used}#view=FitH`} className="pdf" />
            </>
          ) : (
            <EmptyState icon="description" title="No resume attached">
              This application was added by hand without a tailored resume.
            </EmptyState>
          )}
        </aside>
      </div>
    </>
  );
}
