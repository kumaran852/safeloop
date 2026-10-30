import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api, qs } from "../services/api";
import { Json, Page } from "../types";
import { fmtDateTime } from "../utils/format";
import { Async, Card, Empty, Field, LevelBadge, PageHeader, Pager, StatusBadge, useToast } from "../components/ui/ui";

export default function AlertsPage() {
  const { meta } = useMeta();
  const toast = useToast();
  const [f, setF] = useState({ status: "", ward_id: "", task: "", level: "" });
  const [page, setPage] = useState(1), [open, setOpen] = useState<number | null>(null);
  const set = (p: Partial<typeof f>) => { setF({ ...f, ...p }); setPage(1); };
  const { data, loading, error, reload } = useApi<Page<Json>>(`/alerts${qs({ ...f, page, page_size: 15 })}`);
  async function ack(id: number) {
    try { await api.post(`/alerts/${id}/acknowledge`, {}); toast("Alert acknowledged"); reload(); } catch (e) { toast((e as Error).message, "err"); }
  }
  return (
    <>
      <PageHeader title="Alerts centre" subtitle="Ranked by level, then overdue, then unassigned, then age. Every alert links to its report and case." />
      <Card>
        <div className="filters">
          <Field label="Status"><select value={f.status} onChange={(e) => set({ status: e.target.value })}><option value="">All</option><option>New</option><option>Acknowledged</option><option>Closed</option></select></Field>
          <Field label="Level"><select value={f.level} onChange={(e) => set({ level: e.target.value })}><option value="">All</option><option>Critical</option><option>High</option></select></Field>
          <Field label="Ward"><select value={f.ward_id} onChange={(e) => set({ ward_id: e.target.value })}><option value="">All</option>{meta.wards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
          <Field label="Task"><select value={f.task} onChange={(e) => set({ task: e.target.value })}><option value="">All</option>{meta.tasks.map((x) => <option key={x}>{x}</option>)}</select></Field>
        </div>
        <Async loading={loading} error={error} retry={reload}>
          {data && (data.items.length === 0 ? <Empty title="No alerts match" hint="Alerts are created when a report scores High or Critical." /> : <>
            <div className="tbl"><table><thead><tr><th>Level</th><th>Alert</th><th>Ward / task</th><th>Report</th><th>Case</th><th>Status</th><th></th></tr></thead><tbody>
              {data.items.map((a) => <Fragment key={a.id}>
                <tr>
                  <td><LevelBadge level={a.level} /></td>
                  <td>#{a.id}<br /><span className="muted small">{fmtDateTime(a.created_at)}</span></td>
                  <td>{a.ward}<br /><span className="muted small">{a.task} · {a.body_region_label}</span></td>
                  <td>#{a.report_id} · {a.worker}<br /><span className="muted small">score {a.risk_score}, discomfort {a.severity}/10</span></td>
                  <td>{a.case ? <><Link to={`/cases/${a.case.id}`}>{a.case.code}</Link> <StatusBadge status={a.case.status} /><br />{a.unassigned && <span className="chip danger">Unassigned</span>} {a.overdue && <span className="chip danger">Overdue</span>}</> : "—"}</td>
                  <td>{a.status}{a.acknowledged_at && <><br /><span className="muted small">{fmtDateTime(a.acknowledged_at)}</span></>}</td>
                  <td><div className="row">{a.status === "New" && <button className="btn sm primary" onClick={() => ack(a.id)}>Acknowledge</button>}<button className="btn sm" onClick={() => setOpen(open === a.id ? null : a.id)}>{open === a.id ? "Hide" : "Why?"}</button></div></td>
                </tr>
                {open === a.id && <tr><td colSpan={7}><div className="note-box">{a.reason}</div></td></tr>}
              </Fragment>)}
            </tbody></table></div><Pager page={page} total={data.total} pageSize={15} onPage={setPage} /></>)}
        </Async>
      </Card>
    </>
  );
}
