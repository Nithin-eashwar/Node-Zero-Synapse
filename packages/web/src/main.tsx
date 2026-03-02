import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";

const ROUTES = [
  { path: "/blast-radius", title: "Blast Radius" },
  { path: "/smart-blame", title: "Smart Blame" },
  { path: "/patterns", title: "Patterns" },
  { path: "/arch", title: "Arch" }
] as const;

const DEFAULT_PATH = ROUTES[0].path;

function Page({ title }: { title: string }) {
  return <h1>{title}</h1>;
}

function App() {
  return (
    <BrowserRouter>
      <main>
        <nav>
          <ul>
            {ROUTES.map((route) => (
              <li key={route.path}>
                <NavLink to={route.path}>{route.title}</NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <Routes>
          <Route path="/" element={<Navigate replace to={DEFAULT_PATH} />} />
          {ROUTES.map((route) => (
            <Route key={route.path} path={route.path} element={<Page title={route.title} />} />
          ))}
          <Route path="*" element={<Navigate replace to={DEFAULT_PATH} />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
