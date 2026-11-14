import { useState } from "react";
import { api } from "../api.js";
import { Chips, Segmented, Stat } from "../components.jsx";
import { navigate } from "../router.js";

const RESUMES = [
  { value: "ai", label: "AI / ML" },
  { value: "sde", label: "SDE" },
  { value: "fullstack", label: "Full Stack" },
];
const TIER_LABEL = { A3: "proven", B: "learnable", C: "don't have", unverified: "verify", unclassified: "check" };
const pct = (n) => (n == null ? "–" : `${n}%`);
const kwText = (k) => (typeof k === "string" ? k : k?.keyword || "");
const uniq = (xs) => [...new Set((xs || []).map(kwText).filter(Boolean))];

/* ------------------------------------------------------------ step 2: pick */
function PickRow({ item, checked, onToggle }) {
  return (
    <label className={`tr pick ${checked ? "on" : ""}`}>
      <input type="checkbox" checked={checked} onChange={() => onToggle(item.skill)} />
      <span className="strong">{item.text}</span>
      <span className={`badge tier-${item.tier}`}>{TIER_LABEL[item.tier] || item.tier}</span>
      <span className="muted small">
        {item.reason}
        {item.where_to_use ? <span className="faint"> · {item.where_to_use}</span> : null}
      </span>
    </label>
  );
}

function Picker({ data, selected, onToggle, onSetAll, onApply, busy }) {
  const c = data.categories;
  const llm = data.llm || {};
  const groqDown = data.ats_keywords?.error;
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <p className="eyebrow">Step 2 · {data.resume} resume · {data.role_family} role{data.company ? ` · ${data.company}` : ""}</p>
          <h2>Pick what to add</h2>
        </div>
        <span className={`badge ${llm.source === "groq" ? "lime" : "amber"}`}>
          keywords: {llm.source === "groq" ? "Groq" : llm.fallback_used ? "local + role table" : "local"}
        </span>
      </div>
      {groqDown && <p className="error">Groq failed, used the local fallback: {groqDown}</p>}
      <div className="stats">
        <Stat value={c.have.length} label="already have" tone="lime" />
        <Stat value={c.must_add.length} label="must add" tone="amber" />
        <Stat value={c.might_add.length} label="might add" />
        <Stat value={pct(data.mismatch.overall_mismatch_pct)} label="mismatch now" tone="coral" />
      </div>

      <h3>Already on your resume</h3>
      <Chips items={c.have.map((h) => h.text)} tone="lime" />

      <div className="row between pick-head">
        <h3>Must add <span className="faint small">· the JD/ATS ranks these essential and you can back them up</span></h3>
        {c.must_add.length > 0 && (
          <button type="button" className="btn ghost sm" onClick={() => onSetAll(c.must_add, true)}>Select all</button>
        )}
      </div>
      {c.must_add.length
        ? <div className="table">{c.must_add.map((i) => (
            <PickRow key={i.skill} item={i} checked={selected.has(i.skill)} onToggle={onToggle} />))}</div>
        : <p className="faint">Nothing essential is missing.</p>}

      <h3>Might add <span className="faint small">· needs real work first: only tick what you can prove, no bluffing</span></h3>
      {c.might_add.length
        ? <div className="table">{c.might_add.map((i) => (
            <PickRow key={i.skill} item={i} checked={selected.has(i.skill)} onToggle={onToggle} />))}</div>
        : <p className="faint">Nothing else.</p>}

      <div className="row end sticky-bar">
        <span className="muted">{selected.size} selected</span>
        <button type="button" className="btn ghost" disabled={!selected.size || !!busy}
                onClick={() => onSetAll([...c.must_add, ...c.might_add], false)}>Clear</button>
        <button type="button" className="btn primary" disabled={!selected.size || !!busy} onClick={onApply}>
          {busy === "apply" ? <><span className="spin" /> Editing resume…</>
            : `Add ${selected.size || ""} to resume`}
        </button>
      </div>
    </section>
  );
}

/* ------------------------------------------------ step 3: compare + save */
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

function Compare({ done, form, analysis }) {
  const [saved, setSaved] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    if (!form.company.trim()) return setError("Add the company name in the form above first.");
    setSaving(true);
    setError("");
    try {
      setSaved(await api.post("/api/job_hunt", {
        company: form.company.trim(),
        role: form.title.trim(),
        link: form.link.trim() || null,
        resume_used: done.file,
        skills_added: done.skills_added,
        skills_matched: analysis.categories.have.map((h) => h.text),
        skills_lacking: done.skills_lacking,
        jd: form.jd,
        stage: "applied",
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <p className="eyebrow">Step 3 · output/{done.file}</p>
          <h2>Check it side by side</h2>
        </div>
        <div className="row">
          <a className="btn ghost" href={done.url} target="_blank" rel="noreferrer">Open ↗</a>
          {saved
            ? <button type="button" className="btn primary" onClick={() => navigate("/job_hunt")}>Saved ✓ · Open job hunt →</button>
            : <button type="button" className="btn primary" disabled={saving} onClick={save}>
                {saving ? <><span className="spin" /> Saving…</> : "Add to applied jobs"}
              </button>}
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="side">
        <figure>
          <figcaption className="eyebrow">Original</figcaption>
          <iframe title="Original resume" src={`${done.original_url}#view=FitH`} className="pdf" />
        </figure>
        <figure>
          <figcaption className="eyebrow lime">Edited</figcaption>
          <iframe key={done.url} title="Edited resume" src={`${done.url}#view=FitH`} className="pdf" />
        </figure>
      </div>
      <h3>What changed</h3>
      <ChangeRows changelog={done.edit.changelog} noSlot={done.edit.no_slot} />
      {done.skills_lacking?.length > 0 && (
        <>
          <h3>Study these if shortlisted</h3>
          <Chips items={done.skills_lacking} tone="amber" />
        </>
      )}
    </section>
  );
}

/* ------------------------------------------------------ Groq full report */
function KeywordTable({ items }) {
  if (!items?.length) return <span className="faint">none</span>;
  return (
    <div className="table">
      {items.map((x, i) => (
        <div className="tr" key={`${kwText(x)}-${i}`}>
          <span className={`badge ${x.source === "JD" ? "lime" : "amber"}`}>{x.source || "–"}</span>
          <span className="strong">{kwText(x)}</span>
          <span className="faint">{x.where_to_use}</span>
        </div>
      ))}
    </div>
  );
}

function Keywords({ data }) {
  if (!data || data.error) return null;
  const k = data.keywords || {};
  const copyAll = () => navigator.clipboard.writeText(uniq([
    ...(k.must_have_keywords || []), ...(k.good_to_have_keywords || []),
    ...(k.technical_skills || []), ...(k.tools_and_platforms || []),
  ]).join(", "));
  return (
    <details className="card report">
      <summary>
        <span className="eyebrow">ATS keywords · {data.model}</span>
        <h2>Full Groq keyword report</h2>
      </summary>
      <div className="row end">
        <button type="button" className="btn ghost" onClick={copyAll}>Copy keywords</button>
      </div>
      {k.role_summary && <p className="muted">{k.role_summary}</p>}
      <h3>Must have</h3>
      <KeywordTable items={k.must_have_keywords} />
      <h3>Good to have</h3>
      <KeywordTable items={k.good_to_have_keywords} />
      <div className="grid">
        <div><h4>Technical skills</h4><Chips items={uniq(k.technical_skills)} tone="lime" /></div>
        <div><h4>Tools & platforms</h4><Chips items={uniq(k.tools_and_platforms)} tone="lime" /></div>
        <div><h4>Soft skills</h4><Chips items={uniq(k.soft_skills)} /></div>
        <div><h4>Domain</h4><Chips items={uniq(k.domain_keywords)} /></div>
        <div><h4>Action verbs</h4><Chips items={uniq(k.action_verbs)} /></div>
        <div><h4>Title variations</h4><Chips items={uniq(k.job_title_variations)} /></div>
        <div><h4>Avoid</h4><Chips items={uniq(k.keywords_to_avoid)} tone="coral" /></div>
      </div>
      {k.stretch_keywords?.length > 0 && (
        <>
          <h3>Stretch</h3>
          <div className="table">
            {k.stretch_keywords.map((x, i) => (
              <div className="tr" key={i}>
                <span className="badge amber">stretch</span>
                <span className="strong">{kwText(x)}</span>
                <span className="muted small">{x.beginner_friendly_phrasing}</span>
              </div>
            ))}
          </div>
        </>
      )}
      {k.sample_resume_bullets?.length > 0 && (
        <>
          <h3>Sample bullets</h3>
          <ul className="muted">{k.sample_resume_bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>
        </>
      )}
      {k.honesty_note && <p className="faint small">{k.honesty_note}</p>}
    </details>
  );
}

/* ------------------------------------------------------------------ page */
const EMPTY = { resume: "ai", title: "", company: "", link: "", jd: "" };

export default function Tailor() {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [done, setDone] = useState(null);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));

  async function runAnalyze() {
    if (!form.title.trim() || !form.jd.trim()) return setError("Add a job title and paste the JD first.");
    setBusy("analyze");
    setError("");
    setAnalysis(null);
    setDone(null);
    try {
      const a = await api.post("/analyze", {
        resume: form.resume, title: form.title, company: form.company, jd: form.jd,
      });
      setAnalysis(a);
      // safe default: must-adds already proven in your bullets
      setSelected(new Set(a.categories.must_add.filter((i) => i.tier === "A3").map((i) => i.skill)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function runApply() {
    setBusy("apply");
    setError("");
    setDone(null);
    try {
      setDone(await api.post("/apply_selected", { analysis, selected: [...selected] }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  const toggle = (skill) => setSelected((s) => {
    const n = new Set(s);
    n.has(skill) ? n.delete(skill) : n.add(skill);
    return n;
  });
  const setAll = (items, on) => setSelected((s) => {
    const n = new Set(s);
    items.forEach((i) => (on ? n.add(i.skill) : n.delete(i.skill)));
    return n;
  });

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Step 1</p>
        <h1>Tailor a resume<span className="lime">.</span></h1>
        <p className="muted">Paste the job. Groq finds the ATS keywords, Crafter checks them against your resume, and you pick what goes in.</p>
      </section>

      <form className="card form" onSubmit={(e) => { e.preventDefault(); runAnalyze(); }}>
        <div className="field-row">
          <label className="field">
            <span>Resume</span>
            <Segmented name="Resume" options={RESUMES} value={form.resume} onChange={set("resume")} />
          </label>
          <label className="field grow">
            <span>Job title</span>
            <input value={form.title} onChange={set("title")} placeholder="AI Engineer – Fresher" />
          </label>
        </div>
        <div className="field-row">
          <label className="field grow">
            <span>Company</span>
            <input value={form.company} onChange={set("company")} placeholder="Acme Labs" />
          </label>
          <label className="field grow">
            <span>Job link <span className="faint">(optional)</span></span>
            <input type="url" value={form.link} onChange={set("link")} placeholder="https://…" />
          </label>
        </div>
        <label className="field">
          <span>Job description</span>
          <textarea value={form.jd} onChange={set("jd")}
                    placeholder="Paste the full job description. Multi-line is fine." />
        </label>
        <div className="row end">
          {error && <p className="error">{error}</p>}
          <button className="btn primary" disabled={!!busy}>
            {busy === "analyze" ? <><span className="spin" /> Analysing…</> : "Analyze"}
          </button>
        </div>
      </form>

      {analysis && (
        <Picker data={analysis} selected={selected} onToggle={toggle} onSetAll={setAll}
                onApply={runApply} busy={busy} />
      )}
      {done && <Compare key={done.file} done={done} form={form} analysis={analysis} />}
      {analysis && <Keywords data={analysis.ats_keywords} />}
    </>
  );
}
