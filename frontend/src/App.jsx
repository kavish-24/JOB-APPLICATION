import { navigate, usePath } from "./router.js";
import Tailor from "./pages/Tailor.jsx";
import JobHunt from "./pages/JobHunt.jsx";
import JobDetail from "./pages/JobDetail.jsx";
import Profile from "./pages/Profile.jsx";

const ROUTES = [
  { path: "/", label: "Tailor", Page: Tailor },
  { path: "/job_hunt", label: "Job hunt", Page: JobHunt },
  { path: "/profile", label: "Profile", Page: Profile },
];

export default function App() {
  const path = usePath();
  const detail = path.match(/^\/job_hunt\/([^/]+)\/?$/);
  const route = detail ? ROUTES[1] : ROUTES.find((r) => r.path === path) || ROUTES[0];
  return (
    <div className="shell">
      <header className="topbar">
        <a className="brand" href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}>
          <span className="brand-mark" aria-hidden="true" />
          crafter
        </a>
        <nav className="nav">
          {ROUTES.map((r) => (
            <a key={r.path} href={r.path} className={r === route ? "on" : ""}
               onClick={(e) => { e.preventDefault(); navigate(r.path); }}>
              {r.label}
            </a>
          ))}
        </nav>
      </header>
      <main className={`page ${detail ? "wide" : ""}`}>
        {detail ? <JobDetail id={decodeURIComponent(detail[1])} /> : <route.Page />}
      </main>
    </div>
  );
}
