import { useState } from "react";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { qs } from "../services/api";
import { Json } from "../types";
import { fmtDate } from "../utils/format";
import { Async, Card, Chip, Empty, Field, PageHeader } from "../components/ui/ui";

export default function WardIntelligencePage() {
  const { meta } = useMeta();
  const [ward, setWard] = useState(""), [win, setWin] = useState("");
  const { data, loading, error, reload } = useApi<Json>(`/analytics/patterns${qs({ ward_id: ward, window_days: win })}`);
  return (
    <>
      <PageHeader title="Ward intelligence" subtitle="Recurring discomfort by ward, task and body region. Patterns describe recorded reports and do not establish causes." />
      <Card>
        <div className="filters">
          <Field label="Ward"><select value={ward} onChange={(e) => setWard(e.target.value)}><option value="">All wards</option>{meta.wards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
          <Field label="Window"><select value={win} onChange={(e) => setWin(e.target.value)}><option value="">Default</option><option value="14">14 days</option><option value="30">30 days</option><option value="60">60 days</option></select></Field>
        </div>
        <Async loading={loading} error={error} retry={reload}>
          {data && <p className="muted small">Observation window: last {data.window_days} days (since {fmtDate(data.since)}). Sample: {data.sample_size} reports (previous window: {data.previous_window_size}). Flag rule: at least {data.thresholds.min_reports} reports from at least {data.thresholds.min_workers} different workers for the same ward, task and body region. Synthetic share of sample: {data.synthetic_share === null ? "n/a" : `${data.synthetic_share}%`}. Duplicate-flagged reports are excluded.</p>}
        </Async>
      </Card>
      <Async loading={loading} error={error} retry={reload}>
        {data && <>
          <h2 style={{ margin: "6px 0 10px" }}>Flagged clusters ({data.clusters.length})</h2>
          {data.clusters.length === 0 ? <Empty title="No cluster meets the thresholds" hint="Small samples are never flagged on one or two observations." /> : (
            <div className="grid g2">{data.clusters.map((c: Json, i: number) => (
              <Card key={i} title={`${c.ward} · ${c.task} · ${c.region_label}`} actions={<Chip tone="warn">{c.reports} reports</Chip>}>
                <p>{c.why_flagged}</p>
                <div className="row small" style={{ margin: "8px 0" }}>
                  <Chip>{c.distinct_workers} workers</Chip><Chip>avg discomfort {c.avg_severity}/10</Chip><Chip>avg score {c.avg_score}</Chip><Chip>repetitive {c.repetitive_pct}%</Chip><Chip>lifting {c.lifting_pct}%</Chip><Chip>10 h+ shifts {c.long_shift_pct}%</Chip>
                </div>
                <p className="muted small">{fmtDate(c.first_report)} to {fmtDate(c.last_report)} · {c.observed_reports} observed, {c.synthetic_reports} synthetic demo</p>
                <h3>Suggested follow-up</h3><ul>{c.recommendations.map((r: string, j: number) => <li key={j}>{r}</li>)}</ul>
                <p className="muted small">{c.caveat}</p>
              </Card>))}</div>
          )}
          <Card title="Ward trends (current vs previous window)" className="" >
            <div className="tbl"><table><thead><tr><th>Ward</th><th>Reports now</th><th>Previous</th><th>Change</th><th>Avg score</th><th>High / Critical</th></tr></thead><tbody>
              {data.ward_trends.map((w: Json) => <tr key={w.ward}><td>{w.ward}</td><td>{w.current_reports}</td><td>{w.previous_reports}</td><td>{w.change > 0 ? `+${w.change}` : w.change}</td><td>{w.avg_score ?? "n/a"}</td><td>{w.high_or_critical}</td></tr>)}
            </tbody></table></div>
            <p className="muted small">Counts depend on how many workers report and how much exposure each ward has. Rates per worker-hour are not available because exposure hours are not recorded.</p>
          </Card>
        </>}
      </Async>
    </>
  );
}
