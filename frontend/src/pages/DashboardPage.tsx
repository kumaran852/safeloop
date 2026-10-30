import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Plus } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useLang } from "../i18n";
import { Json } from "../types";
import { fmtDate, fmtDateTime, pct } from "../utils/format";
import { Async, Card, Empty, LevelBadge, PageHeader, Stat, StatusBadge } from "../components/ui/ui";

export default function DashboardPage() {
  const { t } = useLang();
  const { data: d, loading, error, reload } = useApi<Json>("/analytics/dashboard");
  return (
    <>
      <PageHeader title={t("nav_dashboard")} subtitle="Live view from the SAFELOOP database" actions={<><Link className="btn primary" to="/reports/new"><Plus size={16} />{t("new_report")}</Link><Link className="btn" to="/cases">Open cases</Link></>} />
      <Async loading={loading} error={error} retry={reload}>
        {d && (d.totals.reports === 0 ? <Empty title="No reports yet" hint="Submit the first worker report to start the loop." action={<Link className="btn primary" to="/reports/new">{t("new_report")}</Link>} /> : (
          <>
            <div className="grid stats" style={{ marginBottom: 14 }}>
              <Stat label="Registered workers" value={d.totals.workers} />
              <Stat label="Reports received" value={d.totals.reports} sub={`${d.totals.synthetic_reports} synthetic demo`} />
              <Stat label="High-priority alerts (active)" value={d.totals.high_priority_alerts} tone="danger" sub={`${d.totals.unacknowledged_alerts} not acknowledged`} />
              <Stat label="Open cases" value={d.totals.open_cases} sub={`${d.totals.unassigned_high_priority} high-priority unassigned`} />
              <Stat label="Overdue interventions" value={d.totals.overdue_cases} tone="warn" />
              <Stat label="Follow-up documented" value={d.totals.followup_rate.pct === null ? "n/a" : `${d.totals.followup_rate.pct}%`} sub={`${d.totals.followup_rate.num}/${d.totals.followup_rate.den} cases with work started`} />
            </div>
            <div className="grid g2">
              <Card title="Weekly reports (last 8 weeks)"><div className="chart"><ResponsiveContainer><BarChart data={d.weekly}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="week" tickFormatter={(v: string) => v.slice(5)} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="reports" name="All reports" fill="#0e7c86" /><Bar dataKey="high_or_critical" name="High / Critical" fill="#b3261e" /></BarChart></ResponsiveContainer></div></Card>
              <Card title="Reports by body region"><div className="chart"><ResponsiveContainer><BarChart data={d.by_region} layout="vertical" margin={{ left: 40 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="label" width={130} /><Tooltip /><Bar dataKey="reports" fill="#193049" /></BarChart></ResponsiveContainer></div></Card>
              <Card title="Average score by ward"><div className="chart"><ResponsiveContainer><BarChart data={d.by_ward}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="ward" /><YAxis domain={[0, 100]} /><Tooltip /><Bar dataKey="avg_score" name="Avg score" fill="#b86e00" /></BarChart></ResponsiveContainer></div><p className="muted small">Average of report scores per ward (operational priority, 0–100). Compare with report counts before drawing conclusions.</p></Card>
              <Card title="Average score by task"><div className="chart"><ResponsiveContainer><BarChart data={d.by_task}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="task" interval={0} tick={{ fontSize: 11 }} /><YAxis domain={[0, 100]} /><Tooltip /><Bar dataKey="avg_score" name="Avg score" fill="#0a5f67" /></BarChart></ResponsiveContainer></div></Card>
            </div>
            <div className="grid g2" style={{ marginTop: 14 }}>
              <Card title="Outstanding actions" actions={<Link to="/cases">All cases</Link>}>
                {d.outstanding_cases.length === 0 ? <Empty title="No outstanding cases" /> : <div className="tbl"><table><thead><tr><th>Case</th><th>Ward</th><th>Level</th><th>Status</th><th>Owner</th><th>Due</th></tr></thead><tbody>
                  {d.outstanding_cases.map((c: Json) => <tr key={c.id}><td><Link to={`/cases/${c.id}`}>{c.code}</Link></td><td>{c.ward}</td><td><LevelBadge level={c.risk_level} /></td><td><StatusBadge status={c.status} /></td><td>{c.owner ?? <span className="chip danger">Unassigned</span>}</td><td>{fmtDate(c.due_date)} {c.overdue && <span className="chip danger">Overdue</span>}</td></tr>)}
                </tbody></table></div>}
              </Card>
              <Card title="Recent reports" actions={<Link to="/reports">All reports</Link>}>
                <div className="tbl"><table><thead><tr><th>When</th><th>Worker</th><th>Ward / task</th><th>Region</th><th>Score</th></tr></thead><tbody>
                  {d.recent_reports.map((r: Json) => <tr key={r.id}><td>{fmtDateTime(r.created_at)}</td><td>{r.worker}</td><td>{r.ward} · {r.task}</td><td>{r.body_region_label}</td><td><LevelBadge level={r.risk_level} /> {r.risk_score}</td></tr>)}
                </tbody></table></div>
              </Card>
            </div>
            <p className="muted small">Follow-up rate = cases with at least one follow-up ÷ cases where work has started. Currently {pct(d.totals.followup_rate)}.</p>
          </>
        ))}
      </Async>
    </>
  );
}
