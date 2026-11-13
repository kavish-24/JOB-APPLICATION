import { useEffect, useState } from "react";

const RESUMES = [
  { value: "ai", label: "AI / ML" },
  { value: "sde", label: "SDE" },
  { value: "fullstack", label: "Full Stack" },
];

const pct = (n) => (n == null ? "–" : `${n}%`);

function Chips({ items, tone }) {
  if (!items?.length) return <span className="muted">none</span>;
  return (
    <div className="chips">
      {items.map((s) => (
        <span key={s} className={`chip ${tone || ""}`}>{s}</span>
      ))}
    </div>
  );
}

function Results({ data }) {
  const m = data.mismatch;
  const s = data.suggested_additions;
  return (
    <section className="results">
      <div className="stats">
        <div className="stat big">
          <div className="num">{pct(m.overall_mismatch_pct)}</div>
          <div className="lbl">overall mismatch</div>
        </div>
        <div className="stat big good">
          <div className="num">{pct(data.mismatch_after_suggested_additions_pct)}</div>
          <div className="lbl">after suggested additions</div>
        </div>
        {["required", "preferred", "implied"].map((b) => (
          <div className="stat" key={b}>
            <div className="num">{pct(m[`${b}_mismatch_pct`])}</div>
            <div className="lbl">{b} · {m[`${b}_missing`]} missing</div>
          </div>
        ))}
      </div>

      <p className="muted">
        Resume: <b>{data.resume}</b> · role family: <b>{data.role_family}</b>
      </p>

      <h3>Already on resume</h3>
      <Chips items={data.skills.matched} tone="ok" />

      <h3>Missing skills</h3>
      <table>
        <thead>
          <tr><th>Skill</th><th>Bucket</th><th>Tier</th><th>Hours</th><th>Note</th></tr>
        </thead>
        <tbody>
          {data.skills.missing.map((x) => (
            <tr key={x.skill}>
              <td>{x.skill}</td>
              <td>{x.bucket}</td>
              <td><span className={`tier t-${x.tier}`}>{x.tier}</span></td>
              <td>{x.hours ?? ""}</td>
              <td>
                {x.experience_gated ? "experience-gated " : ""}
                {x.source ? `via ${x.source}` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Suggested additions</h3>
      <div className="grid">
        <div>
          <h4>Free (A3, already proven)</h4>
          <Chips items={s.free_a3} tone="ok" />
        </div>
        <div>
          <h4>Learn (Tier B, max 4)</h4>
          <Chips items={s.tier_b.map((t) => `${t.skill} (${t.hours}h)`)} tone="warn" />
        </div>
        <div>
          <h4>Overflow (Tier B)</h4>
          <Chips items={s.tier_b_overflow} />
        </div>
        <div>
          <h4>Skip (Tier C)</h4>
          <Chips items={s.skip_tier_c} tone="bad" />
        </div>
        <div>
          <h4>Skip (experience-gated)</h4>
          <Chips items={s.experience_gated_skip} tone="bad" />
        </div>
        <div>
          <h4>Review manually</h4>
          <Chips items={s.review_manually} />
        </div>
      </div>

      <h3>LLM</h3>
      <p className="muted">
        {data.llm.used ? "used" : `not used: ${data.llm.error}`}
        {data.llm.unverified_not_scored?.length > 0 &&
          ` · unscored: ${data.llm.unverified_not_scored.join(", ")}`}
      </p>
    </section>
  );
}

function Composed({ c }) {
  return (
    <section className="results">
      <h3>New TECHNICAL SKILLS section</h3>
      <pre className="section">{c.skills_section}</pre>
      <button type="button" onClick={() => navigator.clipboard.writeText(c.skills_section)}>
        Copy
      </button>

      <h3>Changes</h3>
      {c.changelog.length === 0 && <p className="muted">No changes needed.</p>}
      <table>
        <tbody>
          {c.changelog.map((x, i) => (
            <tr key={i}>
              <td className={x.action === "added" ? "t-A3" : "t-C"}>{x.action}</td>
              <td>{x.skill}</td>
              <td>{x.category}</td>
              <td className="muted">{x.reason}</td>
            </tr>
          ))}
          {c.no_slot.map((x) => (
            <tr key={x.skill}>
              <td className="t-B">no slot</td>
              <td>{x.skill}</td>
              <td>{x.category}</td>
              <td className="muted">{x.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Space (chars per line, must stay ≤ budget)</h3>
      <table>
        <thead><tr><th>Line</th><th>Before</th><th>After</th><th>Budget</th></tr></thead>
        <tbody>
          {Object.entries(c.space).map(([cat, s]) => (
            <tr key={cat}>
              <td>{cat}</td><td>{s.before}</td>
              <td className={s.after > s.budget ? "t-C" : ""}>{s.after}</td>
              <td>{s.budget}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Viewer({ done }) {
  const [which, setWhich] = useState("edited");
  const src = which === "edited" ? done.url : done.original_url;
  const e = done.edit;
  return (
    <section className="results">
      <h3>Resume viewer</h3>
      <div className="toggle">
        <button type="button" className={which === "edited" ? "" : "ghost"}
                onClick={() => setWhich("edited")}>Edited copy</button>
        <button type="button" className={which === "original" ? "" : "ghost"}
                onClick={() => setWhich("original")}>Original</button>
        <a href={done.url} target="_blank" rel="noreferrer">open / download ↗</a>
      </div>
      <p className="muted">Saved as <b>output/{done.file}</b></p>
      <iframe key={src} title="resume" src={`${src}#view=FitH`} className="pdf" />
      <h4>What the tool changed</h4>
      <table>
        <tbody>
          {e.changelog.map((x, i) => (
            <tr key={i}>
              <td className={x.action === "added" ? "t-A3" : "t-C"}>{x.action}</td>
              <td>{x.skill}</td><td>{x.category}</td><td className="muted">{x.reason}</td>
            </tr>
          ))}
          {e.no_slot.map((x) => (
            <tr key={x.skill}>
              <td className="t-B">no slot</td><td>{x.skill}</td><td>{x.category}</td>
              <td className="muted">{x.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function History({ onOpen }) {
  const [files, setFiles] = useState([]);
  useEffect(() => {
    fetch("/outputs").then((r) => r.json()).then(setFiles).catch(() => {});
  }, []);
  if (!files.length) return null;
  return (
    <details>
      <summary>Previous edited copies ({files.length})</summary>
      <ul>
        {files.map((f) => (
          <li key={f.file}><a href={f.url} target="_blank" rel="noreferrer">{f.file}</a></li>
        ))}
      </ul>
    </details>
  );
}

export default function App() {
  const [resume, setResume] = useState("sde");
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [done, setDone] = useState(null);
  const [adding, setAdding] = useState(false);

  async function post(path) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume, title, jd }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    return body;
  }

  async function add() {
    if (!title.trim() || !jd.trim()) return setError("Enter a title and a JD first.");
    setAdding(true);
    setError("");
    setDone(null);
    try {
      const body = await post("/apply");
      setDone(body);
      setData({ analysis: body.analysis, compose: null });
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  }

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setData(null);
    setDone(null);
    try {
      const res = await fetch("/compose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume, title, jd }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
      setData(body);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>JD Gap Analyzer</h1>
      <form onSubmit={submit}>
        <div className="row">
          <select value={resume} onChange={(e) => setResume(e.target.value)}>
            {RESUMES.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Job title, e.g. AI Engineer - Fresher"
            required
          />
        </div>
        <textarea
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste the full job description (multi-line is fine)"
          required
        />
        <div className="actions">
          <button disabled={loading || adding}>{loading ? "Analyzing (~15s)…" : "Preview"}</button>
          <button type="button" className="add" disabled={loading || adding} onClick={add}>
            {adding ? "Editing resume (~20s)…" : "Add to resume"}
          </button>
        </div>
      </form>
      {error && <p className="error">{error}</p>}
      {done && <Viewer done={done} />}
      {data?.compose && <Composed c={data.compose} />}
      {data && <Results data={data.analysis} />}
      <History key={done?.file} />
    </main>
  );
}
