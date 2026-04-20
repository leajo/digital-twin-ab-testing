import { Link, Outlet, useLocation } from "react-router-dom";

const steps = [
  { path: "/", label: "1. 데이터 업로드" },
  { path: "/simulate", label: "2. 시나리오 설정" },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="layout">
      <header className="header">
        <h1>
          <Link to="/" style={{ color: "inherit", textDecoration: "none" }}>
            🧪 Digital Twin A/B Testing
          </Link>
        </h1>
        <nav className="nav">
          {steps.map((s) => (
            <Link
              key={s.path}
              to={s.path}
              className={`nav-link${location.pathname === s.path ? " active" : ""}`}
            >
              {s.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
