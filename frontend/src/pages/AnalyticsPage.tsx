import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Printer } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { exportUrl, qs } from "../services/api";
import { Json } from "../types";
import { hrs, pct } from "../utils/format";
import { Async, Card, Chip, Field, PageHeader, Stat } from "../components/ui/ui";

export default function AnalyticsPage() {
  const { meta } = useMeta();
  const [f, setF] = useState({ date_from: "", date_to: "", ward_id: "" });
  const params = qs(f);
  const { data: d, loading, error, reload } = useApi<Json>(`/analytics/summary${params}`);
  const dq = useApi<Json[]>("/analytics/data-quality");
  const ex = { date_from: f.date_from, date_to: f.date_to, ward_id: f.ward_id };
  return (
    <>
      <PageHeader title="Analytics and reports" subtitle="Definitions and denominators are shown with each metric." actions={<><a className="btn" href={exportUrl("reports.csv", ex)}>Export reports CSV</a><a className="btn" href={exportUrl("cases.csv", ex)}>Export cases CSV</a><button className="btn primary" onClick={() => window.print()}><Printer size={16} />Print / save as PDF</button></>} />
      <Card className="no-print">
        <div className="filters">
          <Field label="From"><input type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} /></Field>
          <Field label="To"><input type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} /></Field>
          <Field label="Ward"><select value={f.ward_id} onChange={(e) => setF({ ...f, ward_id: e.target.value })}><option value="">All wards</option>{meta.wards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
        </div>
      </Card>
      <Async loading={loading} error={error} retry={reload}>
        {d && <>
          <p className="muted small">Filter: {f.date_from || "start"} to {f.date_to || "now"}, {f.ward_id ? meta.wards.find((w) => String(w.id) === f.ward_id)?.name : "all wards"}. Sample: {d.sample.reports} reports ({d.sample.observed_reports} observed, {d.sample.synthetic_reports} synthetic demo), {d.sample.cases} cases. Printed {new Date().toLocaleString("en-IN")}.</p>
          <div className="grid stats" style={{ margin: "10px 0 14px" }}>
            <Stat label="Case completion" value={d.cases.completion_rate.pct === null ? "n/a" : `${d.cases.completion_rate.pct}%`} sub={`Resolved ${d.cases.completion_rate.num} ÷ all cases ${d.cases.completion_rate.den}`} />
            <Stat label="Verified improvement" value={d.cases.verified_improvement.pct === null ? "n/a" : `${d.cases.verified_improvement.pct}%`} sub={`${d.cases.verified_improvement.num} verified ÷ ${d.cases.verified_improvement.den} resolved`} />
            <Stat label="Follow-up documented" value={d.cases.followup_documented.pct === null ? "n/a" : `${d.cases.followup_documented.pct}%`} sub={`${d.cases.followup_documented.num} ÷ ${d.cases.followup_documented.den} cases with work started`} />
            <Stat label="Open / overdue" value={`${d.cases.open} / ${d.cases.overdue}`} tone="warn" sub={`${d.cases.administrative_closures} administrative closures`} />
          </div>
          <div className="grid g2">
            <Card title="Report volume by week"><div className="chart"><ResponsiveContainer><BarChart data={d.weekly_volume}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="week" tickFormatter={(v: string) => v.slice(5)} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="reports" name="Reports" fill="#0e7c86" /><Bar dataKey="high_or_critical" name="High / Critical" fill="#b3261e" /></BarChart></ResponsiveContainer></div></Card>
            <Card title="Risk distribution"><div className="chart"><ResponsiveContainer><BarChart data={d.risk_distribution}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="level" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Reports" fill="#193049" /></BarChart></ResponsiveContainer></div></Card>
            <Card title="Response times">
              <table><tbody>
                <tr><th>Report → alert acknowledged</th><td>{hrs(d.response_times.acknowledgement)}</td></tr>
                <tr><th>Report → first assignment</th><td>{hrs(d.response_times.assignment)}</td></tr>
                <tr><th>Report → work started</th><td>{hrs(d.response_times.intervention)}</td></tr>
              </tbody></table><p className="muted small">{d.response_times.definition}</p>
            </Card>
            <Card title="Repeat reports after intervention">
              <p><strong>{pct({ num: d.repeat_reports.with_repeat_report, den: d.repeat_reports.eligible_interventions, pct: d.repeat_reports.pct })}</strong></p>
              <p className="muted small">{d.repeat_reports.definition}</p>
              <h3>Latest follow-up outcomes</h3>
              <div className="row">{Object.keys(d.cases.latest_outcomes).length === 0 ? <span className="muted">None recorded</span> : Object.entries(d.cases.latest_outcomes).map(([k, v]) => <Chip key={k}>{k}: {String(v)}</Chip>)}</div>
              <p className="muted small">Outcomes show what was observed after interventions. They do not prove the intervention caused any change.</p>
            </Card>
          </div>
          <Card title="Ward and task comparison" >
            <div className="tbl"><table><thead><tr><th>Ward</th><th>Task</th><th>Reports</th><th>Avg score</th><th>High / Critical</th></tr></thead><tbody>
              {d.ward_task.map((r: Json, i: number) => <tr key={i}><td>{r.ward}</td><td>{r.task}</td><td>{r.reports}</td><td>{r.avg_score}</td><td>{r.high_or_critical}</td></tr>)}
            </tbody></table></div>
          </Card>
          {d.unavailable.length > 0 && <p className="warn-box">Unavailable for this filter (no recorded data): {d.unavailable.join(", ")}.</p>}
        </>}
      </Async>
      <Card title="Data quality and coordination checks" className="no-print">
        <Async loading={dq.loading} error={dq.error} retry={dq.reload}>
          {dq.data && <ul className="plain">{dq.data.map((i) => <li key={i.code} style={{ marginBottom: 8 }}>
            <Chip tone={i.count === 0 ? "info" : i.severity === "high" ? "danger" : "warn"}>{i.count}</Chip> <strong>{i.title}</strong> <span className="muted small">{i.count ? i.hint : "No issues"}</span>
            {i.items.length > 0 && <div className="small">{i.items.map((x: Json) => <span key={x.type + x.id} style={{ marginRight: 10 }}>{x.type === "case" ? <Link to={`/cases/${x.id}`}>{x.label}</Link> : x.label}</span>)}</div>}
          </li>)}</ul>}
        </Async>
      </Card>
    </>
  );
}
