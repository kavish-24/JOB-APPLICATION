import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alert, CardHead, Chips, EmptyState, Icon, PageHead, Segmented, Stat } from "../components.jsx";
import { navigate } from "../router.js";

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
        {item.where_to_use ? <span className="faint"> · <b className="muted">{item.where_to_use}</b></span> : null}
      </span>
    </label>
  );
}

function PickTable({ items, selected, onToggle }) {
  return (
    <div className="table">
      <div className="tr pick th" aria-hidden="true">
        <span />
        <span>Keyword / tech</span>
        <span>Readiness</span>
        <span>Context &amp; where to use</span>
      </div>
      {items.map((i) => (
        <PickRow key={i.skill} item={i} checked={selected.has(i.skill)} onToggle={onToggle} />
      ))}
    </div>
  );
}

function Picker({ data, selected, onToggle, onSetAll, onApply, busy }) {
  const c = data.categories;
  const llm = data.llm || {};
  const groqDown = data.ats_keywords?.error;
  const nSel = (items) => items.filter((i) => selected.has(i.skill)).length;
  const picked = [...c.must_add, ...c.might_add].filter((i) => selected.has(i.skill)).map((i) => i.text);
  return (
    <section className="card step">
      <CardHead step="02" eyebrow="Keyword synthesis" title="Pick what to add"
                sub={`${data.title}${data.company ? ` · ${data.company}` : ""} · ${data.resume} resume`}>
        <span className={`badge ${llm.source === "groq" ? "lime" : "amber"}`}>
          <Icon name="bolt" className="sm" />
          keywords: {llm.source === "groq" ? "Groq" : llm.fallback_used ? "local + role table" : "local"}
        </span>
      </CardHead>

      {groqDown && (
        <Alert tone="amber" title="Groq didn't answer, so the local model found the keywords">
          <p>{groqDown}. Matching against your resume still works; current buzzwords may be missed.</p>
        </Alert>
      )}

      <div className="stats">
        <Stat label="Already have" value={c.have.length} icon="check_circle" tone="lime" sub="matched on your resume" />
        <Stat label="Must add" value={c.must_add.length} icon="add_task" tone="lime" sub="essential, can back up" />
        <Stat label="Might add" value={c.might_add.length} icon="help" tone="amber" sub="needs real work first" />
        <Stat label="Mismatch" value={pct(data.mismatch.overall_mismatch_pct)} icon="warning" tone="coral" sub="before any additions" />
      </div>

      <div className="inset">
        <div className="inset-head">
          <span className="title"><Icon name="verified" className="sm lime" />Already on your resume</span>
          <span className="faint small mono">{c.have.length} tags</span>
        </div>
        <Chips items={c.have.map((h) => h.text)} tone="lime" icon="check" empty="nothing from this JD yet" />
      </div>

      <div className="list-title">
        <h3><span className="led" />Must add — the JD/ATS ranks these essential</h3>
        <div className="row">
          <span className="count-note">Selected {nSel(c.must_add)} of {c.must_add.length}</span>
          {c.must_add.length > 0 && (
            <button type="button" className="btn ghost sm" onClick={() => onSetAll(c.must_add, true)}>Select all</button>
          )}
        </div>
      </div>
      {c.must_add.length
        ? <PickTable items={c.must_add} selected={selected} onToggle={onToggle} />
        : <p className="faint small">Nothing essential is missing.</p>}

      <div className="list-title">
        <h3><span className="led amber" />Might add — needs real work first, no bluffing</h3>
        <span className="count-note">Selected {nSel(c.might_add)} of {c.might_add.length}</span>
      </div>
      {c.might_add.length
        ? <PickTable items={c.might_add} selected={selected} onToggle={onToggle} />
        : <p className="faint small">Nothing else.</p>}

      <div className="selection-bar">
        <div className="row">
          <span className="count-tag">{selected.size} SELECTED</span>
          <span className="queued">{picked.length ? `${picked.slice(0, 4).join(", ")}${picked.length > 4 ? "…" : ""} queued` : "Nothing ticked: the resume will be copied as-is"}</span>
        </div>
        <div className="row">
          <button type="button" className="btn ghost sm" disabled={!selected.size || !!busy}
                  onClick={() => onSetAll([...c.must_add, ...c.might_add], false)}>Clear selection</button>
          <button type="button" className="btn primary" disabled={!!busy} onClick={onApply}>
            {busy === "apply" ? <><span className="spin" /> {selected.size ? "Editing resume…" : "Copying…"}</>
              : <>{selected.size ? `Add ${selected.size} to resume` : "Use resume as-is"}<Icon name="arrow_forward" className="sm" /></>}
          </button>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------- step 3: compare */
function ChangeRows({ changelog, noSlot }) {
  if (!changelog.length && !noSlot.length) return <p className="faint small">No changes: this copy is identical to the base resume.</p>;
  return (
    <div className="table">
      {changelog.map((x, i) => (
        <div className="tr" key={i}>
          <span className={`badge ${x.action === "added" ? "lime" : "coral"}`}>
            <Icon name={x.action === "added" ? "add" : "remove"} className="sm" />{x.action}
          </span>
          <span className={x.action === "added" ? "strong" : "strong faint"}>{x.skill}</span>
          <span className="faint small">{x.category}</span>
          <span className="muted small">{x.reason}</span>
        </div>
      ))}
      {noSlot.map((x) => (
        <div className="tr" key={x.skill}>
          <span className="badge amber">no slot</span>
          <span className="strong">{x.skill}</span>
          <span className="faint small">{x.category}</span>
          <span className="muted small">{x.reason}</span>
        </div>
      ))}
    </div>
  );
}

function Compare({ done }) {
  const added = done.edit.changelog.filter((x) => x.action === "added").length;
  const removed = done.edit.changelog.filter((x) => x.action === "removed").length;
  return (
    <section className="card step">
      <CardHead step="03" eyebrow="Diff viewer" title="Check it side by side"
                sub="Only the skills lines changed; the rest of the resume is untouched.">
        <a className="btn ghost sm" href={done.url} target="_blank" rel="noreferrer">Open <Icon name="open_in_new" className="sm" /></a>
      </CardHead>
      <div className="diff">
        <figure>
          <figcaption><span><span className="led" />Original</span><span className="faint">base resume</span></figcaption>
          <iframe title="Original resume" src={`${done.original_url}#view=FitH`} className="pdf" />
        </figure>
        <figure className="edited">
          <figcaption><span><span className="led" />Edited ({done.file})</span><span className="badge lime">+{added} / −{removed}</span></figcaption>
          <iframe key={done.url} title="Edited resume" src={`${done.url}#view=FitH`} className="pdf" />
        </figure>
      </div>
      <div className="inset change-box">
        <div className="inset-head">
          <span className="title">What changed</span>
          <span className="faint small mono">skills section</span>
        </div>
        <ChangeRows changelog={done.edit.changelog} noSlot={done.edit.no_slot} />
        {done.skills_lacking?.length > 0 && (
          <>
            <h4 style={{ margin: "16px 0 8px", color: "var(--amber)" }}>Study these if shortlisted</h4>
            <Chips items={done.skills_lacking} tone="amber" icon="school" />
          </>
        )}
      </div>
    </section>
  );
}

/* ------------------------------------------------ step 4: cover letter */
function CoverLetter({ form, analysis, done, letter, setLetter, makePdf }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function generate() {
    if (letter?.text && !window.confirm("Write a new letter? Your edits to this one will be lost.")) return;
    setBusy("write");
    setError("");
    try {
      const skills = [...(done?.skills_added || []), ...analysis.categories.have.map((h) => h.text)];
      const r = await api.post("/cover_letter", {
        resume: form.resume, title: form.title, company: form.company, jd: form.jd, skills,
      });
      setLetter({ text: r.text, name: r.name, contact: r.contact, file: null, url: null });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  async function download() {
    setBusy("pdf");
    setError("");
    try { window.open((await makePdf()).url, "_blank", "noreferrer"); }
    catch (err) { setError(err.message); }
    finally { setBusy(""); }
  }
  const copy = () => {
    navigator.clipboard.writeText(letter.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="card step">
      <CardHead step="04" eyebrow="Narrative · optional" title="Cover letter"
                sub="A brief 3-paragraph letter written by your local model from your resume, this JD and the company.">
        <button type="button" className={`btn ${letter ? "ghost" : "primary"} sm`} disabled={!!busy} onClick={generate}>
          {busy === "write" ? <><span className="spin" /> Writing…</>
            : <><Icon name="edit_note" className="sm" />{letter ? "Rewrite" : "Write cover letter"}</>}
        </button>
        {letter && (
          <span className="letter-actions">
            <button type="button" className="btn ghost icon" onClick={copy} title="Copy text" aria-label="Copy text">
              <Icon name={copied ? "check" : "content_copy"} className="sm" />
            </button>
            <button type="button" className="btn ghost icon" onClick={download} disabled={!!busy}
                    title="Download PDF" aria-label="Download PDF">
              {busy === "pdf" ? <span className="spin" /> : <Icon name="download" className="sm" />}
            </button>
          </span>
        )}
      </CardHead>
      {error && <Alert tone="coral" icon="error" title="Couldn't write the letter"><p>{error}</p></Alert>}
      {letter ? (
        <>
          <textarea className="letter" aria-label="Cover letter" value={letter.text}
                    onChange={(e) => setLetter((l) => ({ ...l, text: e.target.value, file: null, url: null }))} />
          <p className="hint" style={{ marginTop: 10 }}><Icon name="warning" className="sm amber" />
            Check every fact before sending. Never claim experience you can't back up.</p>
        </>
      ) : !error && (
        <p className="faint small" style={{ margin: 0 }}>You can edit it before copying or downloading; it's saved with the application in step 5.</p>
      )}
    </section>
  );
}

/* --------------------------------------------- step 5: save application */
function SaveBar({ done, form, analysis, letter, makePdf }) {
  const [saved, setSaved] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    if (!form.company.trim()) return setError("Add the company name in step 1 first.");
    setSaving(true);
    setError("");
    try {
      const pdf = letter?.text?.trim() ? await makePdf() : null;
      setSaved(await api.post("/api/job_hunt", {
        company: form.company.trim(),
        role: form.title.trim(),
        link: form.link.trim() || null,
        resume_used: done.file,
        skills_added: done.skills_added,
        skills_matched: analysis.categories.have.map((h) => h.text),
        skills_lacking: done.skills_lacking,
        jd: form.jd,
        cover_letter: letter?.text?.trim() || null,
        cover_letter_file: pdf?.file || null,
        stage: "applied",
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card step">
      <CardHead step="05" eyebrow="Pipeline" title="Track this application"
                sub={`Saves ${form.company || "the company"} · ${form.title}, the JD, resume copy${letter?.text ? ", cover letter" : ""} and skills to study.`}>
        {saved
          ? <button type="button" className="btn primary" onClick={() => navigate(`/job_hunt/${saved.id}`)}>
              Saved ✓ · Open in Job hunt <Icon name="arrow_forward" className="sm" /></button>
          : <button type="button" className="btn primary" disabled={saving} onClick={save}>
              {saving ? <><span className="spin" /> Saving…</> : <>Add to applied jobs <Icon name="arrow_forward" className="sm" /></>}
            </button>}
      </CardHead>
      {error && <p className="error">{error}</p>}
    </section>
  );
}

/* ------------------------------------------------------ Groq full report */
function KeywordTable({ items }) {
  if (!items?.length) return <span className="faint small">none</span>;
  return (
    <div className="table">
      {items.map((x, i) => (
        <div className="tr kw" key={`${kwText(x)}-${i}`}>
          <span className={`badge ${x.source === "JD" ? "lime" : "violet"}`}>{x.source || "–"}</span>
          <span className="strong">{kwText(x)}</span>
          <span className="faint small">{x.where_to_use}</span>
        </div>
      ))}
    </div>
  );
}

function Keywords({ data }) {
  if (!data || data.error) return null;
  const k = data.keywords || {};
  const all = uniq([...(k.must_have_keywords || []), ...(k.good_to_have_keywords || []),
                    ...(k.technical_skills || []), ...(k.tools_and_platforms || [])]);
  return (
    <details className="card report">
      <summary>
        <span className="title"><Icon name="analytics" className="sm lime" />Full Groq keyword report</span>
        <span className="row"><span className="faint small mono">{all.length} keywords · {data.model}</span>
          <Icon name="expand_more" className="chev" /></span>
      </summary>
      <div className="report-body">
        <div className="row between">
          {k.role_summary ? <p className="muted" style={{ margin: 0, flex: "1 1 300px" }}>{k.role_summary}</p> : <span />}
          <button type="button" className="btn ghost sm" onClick={() => navigator.clipboard.writeText(all.join(", "))}>
            <Icon name="content_copy" className="sm" />Copy keywords</button>
        </div>
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
                <div className="tr kw" key={i}>
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
        {k.honesty_note && <p className="hint"><Icon name="info" className="sm" />{k.honesty_note}</p>}
      </div>
    </details>
  );
}

/* ------------------------------------------------------------------ page */
const EMPTY = { resume: "", title: "", company: "", link: "", jd: "" };

export default function Tailor() {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [done, setDone] = useState(null);
  const [resumes, setResumes] = useState(null);
  const [letter, setLetter] = useState(null);   // {text, name, contact, file, url}
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));

  useEffect(() => {
    api.get("/api/resumes").then((rs) => {
      setResumes(rs);
      setForm((f) => (f.resume || !rs.length ? f : { ...f, resume: rs[0].key }));
    }).catch((e) => setError(e.message));
  }, []);

  async function runAnalyze() {
    if (!form.resume) return setError("Upload a base resume on the Profile page first.");
    if (!form.title.trim() || !form.jd.trim()) return setError("Add a job title and paste the JD first.");
    setBusy("analyze");
    setError("");
    setAnalysis(null);
    setDone(null);
    setLetter(null);
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

  // PDF of the current letter text (re-made only when the text changed)
  async function makeLetterPdf() {
    if (letter.file) return letter;
    const r = await api.post("/cover_letter/pdf", {
      text: letter.text, name: letter.name, contact: letter.contact,
      title: form.title, company: form.company, resume: form.resume,
    });
    setLetter((l) => ({ ...l, file: r.file, url: r.url }));
    return r;
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

  const head = (
    <PageHead eyebrow="Resume optimizer · step by step" title="Tailor a resume"
              lede="Paste the job. Groq finds the ATS keywords, crafter checks them against your resume, and you pick what goes in. Nothing is added without your tick." />
  );

  if (resumes && !resumes.length) {
    return (
      <>
        {head}
        <section className="card">
          <EmptyState icon="note_add" title="No base resume yet"
                      actions={<button type="button" className="btn primary" onClick={() => navigate("/profile")}>
                        Upload your first resume <Icon name="arrow_forward" className="sm" /></button>}>
            To start tailoring, add at least one resume category in Profile. crafter finds its skills
            section and compares it against each job you paste here.
          </EmptyState>
        </section>
      </>
    );
  }

  return (
    <div className="tailor">
      {head}

      <form className="card step form" onSubmit={(e) => { e.preventDefault(); runAnalyze(); }}>
        <CardHead step="01" eyebrow="Target role" title="Target job & description">
          {resumes === null ? <span className="faint small">Loading resumes…</span> : (
            <Segmented name="Resume category" value={form.resume} onChange={set("resume")}
                       options={resumes.map((r) => ({ value: r.key, label: r.label || r.key }))} />
          )}
        </CardHead>
        <div className="field-row">
          <label className="field">
            <span>Job title</span>
            <input value={form.title} onChange={set("title")} placeholder="Backend Developer" />
          </label>
          <label className="field">
            <span>Company</span>
            <input value={form.company} onChange={set("company")} placeholder="Swiggy" />
          </label>
          <label className="field">
            <span>Job posting URL <span className="faint">optional</span></span>
            <input type="url" value={form.link} onChange={set("link")} placeholder="https://careers…" />
          </label>
        </div>
        <label className="field">
          <span>Job description <span className="char-count">{form.jd.length.toLocaleString()} chars</span></span>
          <textarea value={form.jd} onChange={set("jd")}
                    placeholder="Paste the full job description. Multi-line is fine." />
        </label>
        <div className="card-foot">
          <span className="hint"><Icon name="info" className="sm" />Groq extracts the keywords · matching against your resume happens locally</span>
          <div className="row">
            {error && <p className="error">{error}</p>}
            <button className="btn primary" disabled={!!busy}>
              {busy === "analyze" ? <><span className="spin" /> Analysing…</> : <>Analyze job <Icon name="arrow_forward" className="sm" /></>}
            </button>
          </div>
        </div>
      </form>

      {analysis && (
        <Picker data={analysis} selected={selected} onToggle={toggle} onSetAll={setAll}
                onApply={runApply} busy={busy} />
      )}
      {done && <Compare key={done.file} done={done} />}
      {analysis && (
        <CoverLetter form={form} analysis={analysis} done={done} letter={letter}
                     setLetter={setLetter} makePdf={makeLetterPdf} />
      )}
      {done && (
        <SaveBar key={done.file} done={done} form={form} analysis={analysis}
                 letter={letter} makePdf={makeLetterPdf} />
      )}
      {analysis && <Keywords data={analysis.ats_keywords} />}
    </div>
  );
}
