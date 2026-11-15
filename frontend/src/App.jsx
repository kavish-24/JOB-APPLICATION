import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { navigate, usePath } from "./router.js";
import Tailor from "./pages/Tailor.jsx";
import JobHunt from "./pages/JobHunt.jsx";
import JobDetail from "./pages/JobDetail.jsx";
import Profile from "./pages/Profile.jsx";
import AccountPanel from "./AccountPanel.jsx";

const ROUTES = [
  { path: "/", label: "Tailor", Page: Tailor },
  { path: "/job_hunt", label: "Job hunt", Page: JobHunt },
  { path: "/profile", label: "Profile", Page: Profile },
];

const go = (to) => (e) => { e.preventDefault(); navigate(to); };

/** Real backend status for the header + footer (refreshed every minute). */
function useStatus(path) {
  const [status, setStatus] = useState(null);
  const load = useCallback(
    () => api.get("/api/status").then(setStatus).catch(() => setStatus(null)), []);
  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [path, load]);
  return [status, load];
}

const GROQ = { ready: ["lime", "Groq ready"], missing: ["coral", "Groq key missing"] };
const LOCAL = { online: ["lime", "Local model online"], offline: ["amber", "Local model offline"],
                unset: ["coral", "Local model not set"] };

function Header({ route, status, onAccount }) {
  const groq = GROQ[status?.groq];
  const local = LOCAL[status?.local_model];
  return (
    <header className="app-header">
      <div className="bar">
        <a className="brand" href="/" onClick={go("/")}>
          <span className="brand-mark" aria-hidden="true" />
          <span>crafter<span className="dot-accent">.</span></span>
        </a>
        <nav className="nav" aria-label="Main">
          {ROUTES.map((r) => (
            <a key={r.path} href={r.path} className={r === route ? "on" : ""}
               aria-current={r === route ? "page" : undefined} onClick={go(r.path)}>
              {r.label}
            </a>
          ))}
        </nav>
        <div className="header-right">
          {groq && <span className="pill optional"><span className={`led ${groq[0]}`} />{groq[1]}</span>}
          {local && (
            <button type="button" className="pill optional clickable" onClick={onAccount}
                    title="Set the local model (ngrok) link">
              <span className={`led ${local[0]}`} />{local[1]}
            </button>
          )}
          <button type="button" className="user-chip" onClick={onAccount} aria-haspopup="dialog" title="Account">
            <span className="avatar">{status?.user?.initials || <span className="ms sm">person</span>}</span>
            <span className="name">{status?.user?.name || "Account"}</span>
            <span className="ms sm faint">expand_more</span>
          </button>
        </div>
      </div>
    </header>
  );
}

function Footer({ status }) {
  return (
    <footer className="app-footer">
      <div className="bar">
        <div>
          <span>crafter // local workspace</span>
          {status && <span><b>{status.resumes}</b> resume categories · <b>{status.jobs}</b> applications</span>}
        </div>
        <div>
          {status ? (
            <>
              <span>keywords: <b>{status.groq === "ready" ? "groq" : "local"}</b></span>
              <span>cover letters: <b>local model {status.local_model}</b></span>
            </>
          ) : <span>backend: <b>unreachable</b></span>}
        </div>
      </div>
    </footer>
  );
}

/** The one app shell: header, page, footer. Pages render only their content. */
export default function App() {
  const path = usePath();
  const detail = path.match(/^\/job_hunt\/([^/]+)\/?$/);
  const route = detail ? ROUTES[1] : ROUTES.find((r) => r.path === path) || ROUTES[0];
  const [status, reloadStatus] = useStatus(path);
  const [account, setAccount] = useState(false);
  const closeAccount = useCallback(() => setAccount(false), []);
  return (
    <div className="shell">
      <Header route={route} status={status} onAccount={() => setAccount(true)} />
      {account && <AccountPanel onClose={closeAccount} onSaved={reloadStatus} />}
      <main className={`page ${detail ? "wide" : ""}`}>
        {detail ? <JobDetail id={decodeURIComponent(detail[1])} /> : <route.Page />}
      </main>
      <Footer status={status} />
    </div>
  );
}
