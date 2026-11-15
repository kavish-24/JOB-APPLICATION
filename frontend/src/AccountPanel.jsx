import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Icon } from "./components.jsx";
import { navigate } from "./router.js";

const STATE = {
  online: ["lime", "Online"],
  offline: ["amber", "Offline"],
  unset: ["coral", "Not set"],
};

/** Account overlay: display name, local model (ngrok) URL, profile link, logout. */
export default function AccountPanel({ onClose, onSaved }) {
  const [s, setS] = useState(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState(null);        // {tone, text}
  const [probe, setProbe] = useState(null);    // {state, detail}
  const panel = useRef(null);

  useEffect(() => {
    api.get("/api/settings").then((d) => {
      setS(d);
      setName(d.display_name);
      setUrl(d.llm_endpoint || d.llm_endpoint_effective || "");
      setProbe(d.local_model);
    }).catch((e) => setMsg({ tone: "coral", text: e.message }));
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    panel.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function save(body, what) {
    setBusy(what);
    setMsg(null);
    try {
      const d = await api.patch("/api/settings", body);
      setS(d);
      setName(d.display_name);
      setProbe(d.local_model);
      setMsg({ tone: "lime", text: what === "name" ? "Name saved." : "Local model URL saved." });
      onSaved();
    } catch (err) {
      setMsg({ tone: "coral", text: err.message });
    } finally {
      setBusy("");
    }
  }
  async function test() {
    setBusy("test");
    setMsg(null);
    try { setProbe(await api.post("/api/settings/test", { llm_endpoint: url.trim() })); }
    catch (err) { setMsg({ tone: "coral", text: err.message }); }
    finally { setBusy(""); }
  }

  const initials = (s?.display_name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  const st = STATE[probe?.state] || STATE.unset;
  const urlChanged = s && url.trim().replace(/\/$/, "") !== (s.llm_endpoint || s.llm_endpoint_effective || "");

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section className="account-panel" role="dialog" aria-modal="true" aria-label="Account" tabIndex={-1} ref={panel}>
        <div className="account-head">
          <span className="avatar lg">{initials || <Icon name="person" className="sm" />}</span>
          <div className="who">
            <b>{s?.display_name || "—"}</b>
            {s?.email && <span className="faint small mono">{s.email}</span>}
          </div>
          <button type="button" className="btn ghost icon" onClick={onClose} aria-label="Close"><Icon name="close" className="sm" /></button>
        </div>

        {!s ? <p className="faint small" style={{ padding: "0 18px" }}>Loading…</p> : (
          <>
            <form className="account-section" onSubmit={(e) => { e.preventDefault(); save({ display_name: name }, "name"); }}>
              <h4>Display name</h4>
              <div className="row nowrap">
                <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60}
                       placeholder={s.resume_name || "Your name"} aria-label="Display name" />
                <button className="btn soft" disabled={busy === "name" || name === s.display_name}>
                  {busy === "name" ? <span className="spin" /> : "Save"}</button>
              </div>
              <p className="faint small">Shown in the header and profile. Leave empty to use the name on your resume{s.resume_name ? ` (${s.resume_name})` : ""}.</p>
            </form>

            <form className="account-section" onSubmit={(e) => { e.preventDefault(); save({ llm_endpoint: url }, "url"); }}>
              <div className="row between">
                <h4>Local model · ngrok link</h4>
                <span className={`badge ${st[0]}`}><span className={`dot ${st[0]}`} />{st[1]}</span>
              </div>
              <input value={url} onChange={(e) => { setUrl(e.target.value); setProbe(null); }} spellCheck={false}
                     placeholder="https://xxxx.ngrok-free.app/predict" aria-label="Local model URL" className="mono" />
              {probe?.detail && <p className={`small ${probe.state === "online" ? "lime" : "amber"}`} style={{ margin: 0 }}>{probe.detail}</p>}
              <div className="row">
                <button type="button" className="btn ghost sm" onClick={test} disabled={!url.trim() || !!busy}>
                  {busy === "test" ? <><span className="spin" /> Testing…</> : <><Icon name="network_check" className="sm" />Test</>}
                </button>
                <button className="btn primary sm" disabled={!!busy || !urlChanged}>
                  {busy === "url" ? <span className="spin" /> : "Save link"}</button>
                {s.llm_endpoint && (
                  <button type="button" className="btn ghost sm" disabled={!!busy}
                          onClick={() => { setUrl(""); save({ llm_endpoint: "" }, "url"); }}>Use .env</button>
                )}
              </div>
              <p className="faint small">
                The full URL your Colab/notebook prints, including the route (e.g. <span className="mono">/predict</span>).
                The local model writes cover letters and is the keyword fallback. Currently using: <b>{s.llm_endpoint_source === "app" ? "this link" : s.llm_endpoint_source === ".env" ? ".env" : "nothing"}</b>.
              </p>
            </form>

            {msg && <p className={`account-msg ${msg.tone}`}>{msg.text}</p>}

            <div className="account-links">
              <button type="button" className="menu-item" onClick={() => { onClose(); navigate("/profile"); }}>
                <Icon name="badge" className="sm" />Profile &amp; resume categories<Icon name="chevron_right" className="sm push" />
              </button>
              <button type="button" className="menu-item danger"
                      onClick={() => setMsg({ tone: "amber", text: "Sign-in isn't set up yet, so there's nothing to log out of. It arrives with the database." })}>
                <Icon name="logout" className="sm" />Log out
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
