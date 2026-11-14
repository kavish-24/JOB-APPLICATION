import { navigate, usePath } from "./router.js";
import Tailor from "./pages/Tailor.jsx";
import JobHunt from "./pages/JobHunt.jsx";

const ROUTES = [
  { path: "/", label: "Tailor", Page: Tailor },
  { path: "/job_hunt", label: "Job hunt", Page: JobHunt },
];

export default function App() {
  const path = usePath();
  const route = ROUTES.find((r) => r.path === path) || ROUTES[0];
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
      <main className="page">
        <route.Page />
      </main>
    </div>
  );
}
