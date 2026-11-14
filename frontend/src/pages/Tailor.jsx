import { useState } from "react";
import { api } from "../api.js";
import { Chips, Segmented, Stat } from "../components.jsx";
import { navigate } from "../router.js";

const RESUMES = [
  { value: "ai", label: "AI / ML" },
  { value: "sde", label: "SDE" },
  { value: "fullstack", label: "Full Stack" },
];
const pct = (n) => (n == null ? "–" : `${n}%`);

function ChangeRows({ changelog, noSlot }) {
  return (
    <div className="table">
      {changelog.map((x, i) => (
        <div className="tr" key={i}>
          <span className={`badge ${x.action === "added" ? "lime" : "coral"}`}>{x.action}</span>
          <span className="strong">{x.skill}</span>
          <span className="faint">{x.category}</span>
          <span className="muted small">{x.reason}</span>
        </div>
      ))}
      {noSlot.map((x) => (
        <div className="tr" key={x.skill}>
          <span className="badge amber">no slot</span>
          <span className="strong">{x.skill}</span>
          <span className="faint">{x.category}</span>
          <span className="muted small">{x.reason}</span>
        </div>
      ))}
      {!changelog.length && !noSlot.length && <p className="faint">No changes needed.</p>}
    </div>
  );
}

function Viewer({ done, title }) {
  const [which, setWhich] = useState("edited");
  const src = which === "edited" ? done.url : done.original_url;
  const track = () => {
    sessionStorage.setItem("prefill", JSON.stringify({
      role: title, resume_used: done.file, skills_lacking: done.skills_lacking || [],
    }));
    navigate("/job_hunt");
  };
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <p className="eyebrow">Resume copy</p>
          <h2>output/{done.file}</h2>
        </div>
        <div className="row">
          <Segmented name="Version" value={which} onChange={setWhich}
                     options={[{ value: "edited", label: "Edited" }, { value: "original", label: "Original" }]} />
          <a className="btn ghost" href={done.url} target="_blank" rel="noreferrer">Open ↗</a>
          <button type="button" className="btn primary" onClick={track}>Track application →</button>
        </div>
      </div>
      <iframe key={src} title="Resume" src={`${src}#view=FitH`} className="pdf" />
      <h3>What the MCP tool changed</h3>
      <ChangeRows changelog={done.edit.changelog} noSlot={done.edit.no_slot} />
      {done.skills_lacking?.length > 0 && (
        <>
          <h3>Skills you lack for this job</h3>
          <Chips items={done.skills_lacking} tone="amber" />
        </>
      )}
    </section>
  );
}

function Preview({ c }) {
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <p className="eyebrow">Preview</p>
          <h2>New technical skills section</h2>
        </div>
        <button type="button" className="btn ghost"
                onClick={() => navigator.clipboard.writeText(c.skills_section)}>Copy</button>
      </div>
      <pre className="code">{c.skills_section}</pre>
      <h3>Changes</h3>
      <ChangeRows changelog={c.changelog} noSlot={c.no_slot} />
      <h3>Line widths (pt)</h3>
      <div className="table">
        {Object.entries(c.space).map(([cat, s]) => (
          <div className="tr space" key={cat}>
            <span>{cat}</span>
            <span className="meter"><i style={{ width: `${Math.min(100, (s.after / s.budget) * 100)}%` }} /></span>
            <span className="mono small">{s.before} → {s.after} / {s.budget}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Analysis({ data }) {
  const m = data.mismatch;
  const s = data.suggested_additions;
  const sig = data.signals || { in_title: [], ats_hints: [], most_emphasised: [] };
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <p className="eyebrow">Analysis · {data.resume} resume · {data.role_family} role</p>
          <h2>JD match</h2>
        </div>
        <span className={`badge ${data.llm.used ? "lime" : "amber"}`}>
          LLM {data.llm.used ? (data.llm.fallback_used ? "used + fallback" : "used") : "off"}
        </span>
      </div>
      <div className="stats">
        <Stat value={pct(m.overall_mismatch_pct)} label="mismatch" tone="coral" />
        <Stat value={pct(data.mismatch_after_suggested_additions_pct)} label="after additions" tone="lime" />
        {["required", "preferred", "implied"].map((b) => (
          <Stat key={b} value={pct(m[`${b}_mismatch_pct`])} label={`${b} · ${m[`${b}_missing`]}`} />
        ))}
      </div>
      {(sig.in_title.length > 0 || sig.ats_hints.length > 0 || sig.most_emphasised.length > 0) && (
        <p className="muted signals">
          {sig.in_title.length > 0 && <>Title: <b>{sig.in_title.join(", ")}</b> · </>}
          {sig.ats_hints.length > 0 && <>ATS hints: <b>{sig.ats_hints.join(", ")}</b> · </>}
          {sig.most_emphasised.length > 0 && <>Stressed: <b>{sig.most_emphasised.join(", ")}</b></>}
        </p>
      )}
      <h3>Already on your resume</h3>
      <Chips items={data.skills.matched} tone="lime" />
      <h3>Missing</h3>
      <div className="table">
        {data.skills.missing.map((x) => (
          <div className="tr" key={x.skill}>
            <span className="strong">{x.skill}</span>
            <span className="faint">{x.bucket}</span>
            <span className={`badge tier-${x.tier}`}>{x.tier}</span>
            <span className="muted small">
              {x.hours != null ? `${x.hours}h · ` : ""}
              {x.experience_gated ? "experience-gated · " : ""}
              {x.source}
            </span>
          </div>
        ))}
      </div>
      <div className="grid">
        <div><h4>Free (proven in bullets)</h4><Chips items={s.free_a3} tone="lime" /></div>
        <div><h4>Learn / verify</h4>
          <Chips items={s.tier_b.map((t) => (t.hours != null ? `${t.skill} · ${t.hours}h` : `${t.skill} · verify`))} tone="amber" />
        </div>
        <div><h4>Overflow</h4><Chips items={s.tier_b_overflow} /></div>
        <div><h4>Skip (Tier C)</h4><Chips items={s.skip_tier_c} tone="coral" /></div>
        <div><h4>Skip (years required)</h4><Chips items={s.experience_gated_skip} tone="coral" /></div>
      </div>
    </section>
  );
}

export default function Tailor() {
  const [resume, setResume] = useState("ai");
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [done, setDone] = useState(null);

  async function run(kind) {
    if (!title.trim() || !jd.trim()) return setError("Add a job title and paste the JD first.");
    setBusy(kind);
    setError("");
    setPreview(null);
    setDone(null);
    try {
      const body = { resume, title, jd };
      if (kind === "preview") setPreview(await api.post("/compose", body));
      else setDone(await api.post("/apply", body));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Step 1</p>
        <h1>Tailor a resume<span className="lime">.</span></h1>
        <p className="muted">Paste a JD. Crafter finds the keywords an ATS will search, then fits them into your resume without changing the layout.</p>
      </section>

      <form className="card form" onSubmit={(e) => { e.preventDefault(); run("preview"); }}>
        <div className="field-row">
          <label className="field">
            <span>Resume</span>
            <Segmented name="Resume" options={RESUMES} value={resume} onChange={setResume} />
          </label>
          <label className="field grow">
            <span>Job title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
                   placeholder="AI Engineer – Fresher" />
          </label>
        </div>
        <label className="field">
          <span>Job description</span>
          <textarea value={jd} onChange={(e) => setJd(e.target.value)}
                    placeholder="Paste the full job description. Multi-line is fine." />
        </label>
        <div className="row end">
          {error && <p className="error">{error}</p>}
          <button className="btn ghost" disabled={!!busy}>
            {busy === "preview" ? <><span className="spin" /> Analysing…</> : "Preview"}
          </button>
          <button type="button" className="btn primary" disabled={!!busy} onClick={() => run("apply")}>
            {busy === "apply" ? <><span className="spin" /> Editing resume…</> : "Add to resume"}
          </button>
        </div>
      </form>

      {done && <Viewer done={done} title={title} />}
      {preview && <Preview c={preview.compose} />}
      {(done || preview) && <Analysis data={(done || preview).analysis} />}
    </>
  );
}
