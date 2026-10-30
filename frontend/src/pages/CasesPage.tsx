import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { exportUrl, qs } from "../services/api";
import { Json, Page } from "../types";
import { fmtDate } from "../utils/format";
import { Async, Card, Empty, Field, LevelBadge, PageHeader, Pager, StatusBadge } from "../components/ui/ui";

export default function CasesPage() {
  const { meta } = useMeta();
  const [f, setF] = useState({ status: "", ward_id: "", risk_level: "", overdue: "", unassigned: "" });
  const [page, setPage] = useState(1);
  const set = (p: Partial<typeof f>) => { setF({ ...f, ...p }); setPage(1); };
  const { data, loading, error, reload } = useApi<Page<Json>>(`/cases${qs({ ...f, page, page_size: 15 })}`);
  return (
    <>
      <PageHeader title="Intervention cases" subtitle="Each case links a report to an owner, an action, a due date and evidence of follow-up." actions={<a className="btn" href={exportUrl("cases.csv", {})}>Export CSV</a>} />
      <Card>
        <div className="filters">
          <Field label="Status"><select value={f.status} onChange={(e) => set({ status: e.target.value })}><option value="">All</option>{meta.statuses.map((s) => <option key={s}>{s}</option>)}</select></Field>
          <Field label="Level"><select value={f.risk_level} onChange={(e) => set({ risk_level: e.target.value })}><option value="">All</option>{meta.levels.map((s) => <option key={s}>{s}</option>)}</select></Field>
          <Field label="Ward"><select value={f.ward_id} onChange={(e) => set({ ward_id: e.target.value })}><option value="">All</option>{meta.wards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
          <Field label="Overdue"><select value={f.overdue} onChange={(e) => set({ overdue: e.target.value })}><option value="">Any</option><option value="true">Overdue only</option></select></Field>
          <Field label="Owner"><select value={f.unassigned} onChange={(e) => set({ unassigned: e.target.value })}><option value="">Any</option><option value="true">Unassigned only</option></select></Field>
        </div>
        <Async loading={loading} error={error} retry={reload}>
          {data && (data.items.length === 0 ? <Empty title="No cases match" hint="Cases open automatically for High and Critical reports." /> : <>
            <div className="tbl"><table><thead><tr><th>Case</th><th>Ward / task</th><th>Region</th><th>Level</th><th>Status</th><th>Owner</th><th>Due</th><th>Follow-ups</th></tr></thead><tbody>
              {data.items.map((c) => <tr key={c.id}><td><Link to={`/cases/${c.id}`}>{c.code}</Link></td><td>{c.ward}<br /><span className="muted small">{c.task}</span></td><td>{c.body_region_label}</td><td><LevelBadge level={c.risk_level} /></td><td><StatusBadge status={c.status} />{c.resolution_type === "administrative_closure" && <><br /><span className="chip warn">Admin closure</span></>}{c.resolution_type === "verified_improvement" && <><br /><span className="chip info">Verified</span></>}</td><td>{c.owner ?? <span className="chip danger">Unassigned</span>}</td><td>{fmtDate(c.due_date)} {c.overdue && <span className="chip danger">Overdue</span>}</td><td>{c.follow_up_count}{c.latest_outcome ? ` (${c.latest_outcome})` : ""}</td></tr>)}
            </tbody></table></div><Pager page={page} total={data.total} pageSize={15} onPage={setPage} /></>)}
        </Async>
      </Card>
    </>
  );
}
