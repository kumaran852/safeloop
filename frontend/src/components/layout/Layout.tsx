import { ReactNode, useState } from "react";
import { NavLink } from "react-router-dom";
import { Activity, BarChart3, Bell, Briefcase, ClipboardList, LayoutDashboard, Map, Menu, Plus, Settings, Users } from "lucide-react";
import { useLang } from "../../i18n";
import { Key } from "../../i18n/en";

const NAV: { to: string; key: Key; icon: ReactNode }[] = [
  { to: "/", key: "nav_dashboard", icon: <LayoutDashboard size={18} /> },
  { to: "/workers", key: "nav_workers", icon: <Users size={18} /> },
  { to: "/reports", key: "nav_reports", icon: <ClipboardList size={18} /> },
  { to: "/alerts", key: "nav_alerts", icon: <Bell size={18} /> },
  { to: "/cases", key: "nav_cases", icon: <Briefcase size={18} /> },
  { to: "/wards", key: "nav_wards", icon: <Map size={18} /> },
  { to: "/analytics", key: "nav_analytics", icon: <BarChart3 size={18} /> },
  { to: "/settings", key: "nav_settings", icon: <Settings size={18} /> },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { t, lang, setLang } = useLang();
  const [open, setOpen] = useState(false);
  return (
    <div className="shell">
      <a href="#main" className="skip">Skip to content</a>
      <aside className={`side ${open ? "open" : ""}`}>
        <div className="brand"><Activity size={22} /><div><strong>SAFELOOP</strong><span>From worker signals to verified safety action</span></div></div>
        <nav aria-label="Main">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} onClick={() => setOpen(false)} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.icon}<span>{t(n.key)}</span>
            </NavLink>
          ))}
        </nav>
        <div className="side-foot">Decision-support prototype. Not a medical or injury-prediction system.</div>
      </aside>
      <div className="main">
        <div className="topbar">
          <button className="icon-btn menu" onClick={() => setOpen(!open)} aria-label="Toggle menu"><Menu size={20} /></button>
          <span className="demo">{t("demo_banner")}</span>
          <div className="row">
            <div className="seg" role="group" aria-label={t("language")}>
              <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")} aria-pressed={lang === "en"}>English</button>
              <button className={lang === "ta" ? "on" : ""} onClick={() => setLang("ta")} aria-pressed={lang === "ta"}>தமிழ்</button>
            </div>
            <NavLink to="/reports/new" className="btn primary"><Plus size={16} />{t("new_report")}</NavLink>
          </div>
        </div>
        <main id="main" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
