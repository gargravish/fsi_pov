import { NavLink, Route, Routes } from "react-router-dom";
import {
  LayoutDashboard, Combine, Network, ShieldAlert, TrendingUp, MessagesSquare,
  FileSearch, GitGraph, Boxes, Bot,
} from "lucide-react";
import Home from "./pages/Home";
import Unify from "./pages/Unify";
import Nba from "./pages/Nba";
import Retention from "./pages/Retention";
import Forecast from "./pages/Forecast";
import Ask from "./pages/Ask";
import Research from "./pages/Research";
import NetworkGuard from "./pages/NetworkGuard";
import Segments from "./pages/Segments";
import Agents from "./pages/Agents";

const NAV = [
  { to: "/", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/unify", label: "Unify & Resolve", icon: Combine },
  { to: "/nba", label: "Next-Best-Action", icon: Network },
  { to: "/retention", label: "Flight-Risk Sentinel", icon: ShieldAlert },
  { to: "/forecast", label: "Forecast Room", icon: TrendingUp },
  { to: "/ask", label: "Ask Helix", icon: MessagesSquare },
  { to: "/research", label: "Research Brain", icon: FileSearch },
  { to: "/network", label: "Network Guard", icon: GitGraph },
  { to: "/segments", label: "Segment Studio", icon: Boxes },
  { to: "/agents", label: "Agent Console", icon: Bot },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 shrink-0 border-r border-edge bg-panel/60 p-4 flex flex-col gap-1 sticky top-0 h-screen">
        <div className="flex items-center gap-2 px-2 mb-5">
          <div className="h-9 w-9 rounded-xl bg-accent grid place-items-center font-extrabold text-white">U</div>
          <div>
            <div className="font-extrabold text-white leading-tight">FSI Helix</div>
            <div className="text-[10px] text-muted tracking-wide">AGENTIC DATA PLATFORM</div>
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <n.icon size={17} /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto text-[10px] text-muted/70 px-2 leading-relaxed">
          Synthetic data · POV demo<br />Google Cloud · BigQuery AI
        </div>
      </aside>

      <main className="flex-1 p-7 max-w-[1400px]">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/unify" element={<Unify />} />
          <Route path="/nba" element={<Nba />} />
          <Route path="/retention" element={<Retention />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/research" element={<Research />} />
          <Route path="/network" element={<NetworkGuard />} />
          <Route path="/segments" element={<Segments />} />
          <Route path="/agents" element={<Agents />} />
        </Routes>
      </main>
    </div>
  );
}
