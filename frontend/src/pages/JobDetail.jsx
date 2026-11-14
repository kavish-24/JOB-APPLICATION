import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Chips, TagInput } from "../components.jsx";
import { navigate } from "../router.js";
import { STAGES, TONE, fmtDate } from "./JobHunt.jsx";

export default function JobDetail({ id }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState("");

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
    const copy = job.resume_used ? ` and its resume copy (${job.resume_used})` : "";
    if (!window.confirm(`Delete ${job.company} – ${job.role}${copy}? This can't be undone.`)) return;
    try { await api.del(`/api/job_hunt/${id}`); navigate("/job_hunt"); }
    catch (err) { setError(err.message); }
  };

  const back = (
    <a className="link back" href="/job_hunt" onClick={(e) => { e.preventDefault(); navigate("/job_hunt"); }}>
      ← All applications
    </a>
  );
  if (!job)
    return <>{back}{error ? <p className="error">{error}</p> : <p className="faint">Loading…</p>}</>;

  const { label, ago } = fmtDate(job.applied_date);
  return (
    <>
      {back}
      <div className="detail-split">
        <div className="detail-left">
          <section className="card">
            <div className="card-head">
              <div>
                <p className="eyebrow">Applied {label} · {ago}</p>
                <h2>{job.company}</h2>
                <p className="muted detail-role">{job.role}</p>
              </div>
              <select className={`stage-select ${TONE[job.stage]}`} value={job.stage}
                      onChange={(e) => patch({ stage: e.target.value })} aria-label="Stage">
                {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
            {error && <p className="error">{error}</p>}
            {job.link && (<><h4>Job post</h4>
              <a className="link" href={job.link} target="_blank" rel="noreferrer">{job.link} ↗</a></>)}

            <h3>Added to resume</h3>
            <Chips items={job.skills_added} tone="lime" />
            <h3>Already matched</h3>
            <Chips items={job.skills_matched} />
            <h3>Skills I lack <span className="faint small">· study these if shortlisted</span></h3>
            <TagInput value={job.skills_lacking} onChange={(v) => patch({ skills_lacking: v })} />

            <h3>Notes</h3>
            <textarea className="short" value={notes} onChange={(e) => setNotes(e.target.value)}
                      onBlur={() => notes !== (job.notes || "") && patch({ notes: notes || null })}
                      placeholder="Referral, recruiter name, round details…" />

            <h3>Timeline</h3>
            <ol className="timeline">
              {(job.stage_history || []).map((h, i) => (
                <li key={i}><span className={`dot ${TONE[h.stage]}`} />{h.stage}
                  <span className="faint mono"> {h.at.replace("T", " ").slice(0, 16)}</span></li>
              ))}
            </ol>

            {job.cover_letter && (
              <>
                <div className="row between letter-head">
                  <h3>Cover letter</h3>
                  <div className="row">
                    <button type="button" className="btn ghost sm"
                            onClick={() => navigator.clipboard.writeText(job.cover_letter)}>Copy text</button>
                    {job.cover_letter_file && (
                      <a className="btn ghost sm" href={`/files/${job.cover_letter_file}`} target="_blank" rel="noreferrer">PDF ↗</a>
                    )}
                  </div>
                </div>
                <p className="muted letter-text">{job.cover_letter}</p>
              </>
            )}

            {job.jd && (
              <details className="jd-block">
                <summary className="eyebrow">Job description</summary>
                <p className="muted jd-text">{job.jd}</p>
              </details>
            )}
            <div className="row end">
              <button type="button" className="btn danger" onClick={remove}>Delete</button>
            </div>
          </section>
        </div>

        <aside className="detail-right">
          {job.resume_used ? (
            <>
              <div className="row between">
                <span className="eyebrow">Resume sent · {job.resume_used}</span>
                <a className="link" href={`/files/${job.resume_used}`} target="_blank" rel="noreferrer">Open ↗</a>
              </div>
              <iframe title="Resume used" src={`/files/${job.resume_used}#view=FitH`} className="pdf" />
            </>
          ) : (
            <div className="empty"><p className="strong">No resume attached.</p>
              <p className="faint">This application was added without a tailored resume.</p></div>
          )}
        </aside>
      </div>
    </>
  );
}
