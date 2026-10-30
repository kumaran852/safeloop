import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { exportUrl, qs } from "../services/api";
import { Json, Page } from "../types";
import { fmtDateTime } from "../utils/format";
import { Async, Card, Empty, Field, LevelBadge, Modal, PageHeader, Pager, StatusBadge, SyntheticTag } from "../components/ui/ui";

export default function ReportsPage() {
  const { meta } = useMeta();
  const [f, setF] = useState({ ward_id: "", task: "", risk_level: "", body_region: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1), [sel, setSel] = useState<number | null>(null);
  const set = (p: Partial<typeof f>) => { setF({ ...f, ...p }); setPage(1); };
  const { data, loading, error, reload } = useApi<Page<Json>>(`/reports${qs({ ...f, page, page_size: 15 })}`);
  const det = useApi<Json>(sel ? `/reports/${sel}` : null);
  return (
    <>
      <PageHeader title="Reports" subtitle="Worker-submitted discomfort reports with explainable scores" actions={<><a className="btn" href={exportUrl("reports.csv", f)}>Export CSV</a><Link className="btn primary" to="/reports/new"><Plus size={16} />New report</Link></>} />
      <Card>
        <div className="filters">
          <Field label="Ward"><select value={f.ward_id} onChange={(e) => set({ ward_id: e.target.value })}><option value="">All</option>{meta.wards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
          <Field label="Task"><select value={f.task} onChange={(e) => set({ task: e.target.value })}><option value="">All</option>{meta.tasks.map((x) => <option key={x}>{x}</option>)}</select></Field>
          <Field label="Level"><select value={f.risk_level} onChange={(e) => set({ risk_level: e.target.value })}><option value="">All</option>{meta.levels.map((x) => <option key={x}>{x}</option>)}</select></Field>
          <Field label="Body region"><select value={f.body_region} onChange={(e) => set({ body_region: e.target.value })}><option value="">All</option>{meta.body_regions.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</select></Field>
          <Field label="From"><input type="date" value={f.date_from} onChange={(e) => set({ date_from: e.target.value })} /></Field>
          <Field label="To"><input type="date" value={f.date_to} onChange={(e) => set({ date_to: e.target.value })} /></Field>
        </div>
        <Async loading={loading} error={error} retry={reload}>
          {data && (data.items.length === 0 ? <Empty title="No reports match these filters" /> : <>
            <div className="tbl"><table><thead><tr><th>#</th><th>When</th><th>Worker</th><th>Ward / task</th><th>Region</th><th>Severity</th><th>Score</th><th>Case</th></tr></thead><tbody>
              {data.items.map((r) => <tr key={r.id} className="click" onClick={() => setSel(r.id)}><td>{r.id}</td><td>{fmtDateTime(r.created_at)}</td><td>{r.worker} {r.is_synthetic && <SyntheticTag />}</td><td>{r.ward} · {r.task}</td><td>{r.body_region_label}</td><td>{r.severity}/10</td><td><LevelBadge level={r.risk_level} /> {r.risk_score}</td><td>{r.case_status ? <StatusBadge status={r.case_status} /> : "—"}{r.duplicate_of_id && <span className="chip warn">Possible duplicate</span>}</td></tr>)}
            </tbody></table></div><Pager page={page} total={data.total} pageSize={15} onPage={setPage} /></>)}
        </Async>
      </Card>
      {sel && (
        <Modal wide title={`Report #${sel}`} onClose={() => setSel(null)}>
          <Async loading={det.loading} error={det.error} retry={det.reload}>{det.data && (() => { const r = det.data; return <>
            <div className="row"><LevelBadge level={r.risk_level} /><strong>Score {r.risk_score}/100</strong>{r.is_synthetic && <SyntheticTag />}{r.case && <Link className="btn sm" to={`/cases/${r.case.id}`}>Open {r.case.code}</Link>}</div>
            <p>{r.worker} · {r.ward} · {r.task} · {r.body_region_label} · discomfort {r.severity}/10 · {r.shift_hours} h {r.shift_type} shift · repetitive: {r.repetitive ? "yes" : "no"} · frequent lifting: {r.frequent_lifting ? "yes" : "no"}</p>
            {r.description && <p className="note-box">{r.description}</p>}
            <h3>Why this score</h3><ul className="plain contrib">{r.contributions.map((c: Json, i: number) => <li key={i}><span>{c.detail}</span><strong>{c.points ? `+${c.points}` : ""}</strong></li>)}</ul>
            <p className="muted small">Submitted {fmtDateTime(r.created_at)}. Operational priority only; not a diagnosis.</p></>; })()}</Async>
        </Modal>
      )}
    </>
  );
}
