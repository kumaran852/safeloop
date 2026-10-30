import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api, qs } from "../services/api";
import { Json, Page } from "../types";
import { fmtDateTime } from "../utils/format";
import { Async, Card, Empty, Field, LevelBadge, Modal, PageHeader, Pager, StatusBadge, SyntheticTag, useDebounced, useToast } from "../components/ui/ui";

export default function WorkersPage() {
  const { meta } = useMeta();
  const toast = useToast();
  const [q, setQ] = useState(""), [ward, setWard] = useState(""), [task, setTask] = useState(""), [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, loading, error, reload } = useApi<Page<Json>>(`/workers${qs({ q: dq, ward_id: ward, task, page, page_size: 15 })}`);
  const [edit, setEdit] = useState<Json | "new" | null>(null);
  const [detail, setDetail] = useState<number | null>(null);
  const [form, setForm] = useState({ pseudo_id: "", ward_id: "", task: "", shift_type: "Morning", active: true });
  const open = (w: Json | "new") => { setEdit(w); setForm(w === "new" ? { pseudo_id: "", ward_id: "", task: "", shift_type: "Morning", active: true } : { pseudo_id: w.pseudo_id, ward_id: String(w.ward_id), task: w.task, shift_type: w.shift_type, active: w.active }); };
  async function save() {
    try {
      const body = { ward_id: Number(form.ward_id), task: form.task, shift_type: form.shift_type, active: form.active };
      if (edit === "new") await api.post("/workers", { ...body, pseudo_id: form.pseudo_id.trim() || undefined });
      else await api.patch(`/workers/${(edit as Json).id}`, body);
      toast("Worker saved"); setEdit(null); reload();
    } catch (e) { toast((e as Error).message, "err"); }
  }
  const det = useApi<Json>(detail ? `/workers/${detail}` : null);
  return (
    <>
      <PageHeader title="Workers" subtitle="Pseudonymous worker IDs only. No names or contact details are stored." actions={<button className="btn primary" onClick={() => open("new")}><Plus size={16} />Add worker</button>} />
      <Card>
        <div className="filters">
          <Field label="Search worker ID"><input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="SW-00…" /></Field>
          <Field label="Ward"><select value={ward} onChange={(e) => { setWard(e.target.value); setPage(1); }}><option value="">All</option>{meta.wards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
          <Field label="Task"><select value={task} onChange={(e) => { setTask(e.target.value); setPage(1); }}><option value="">All</option>{meta.tasks.map((x) => <option key={x}>{x}</option>)}</select></Field>
        </div>
        <Async loading={loading} error={error} retry={reload}>
          {data && (data.items.length === 0 ? <Empty title="No workers match" hint="Change the filters or add a worker." /> : (
            <><div className="tbl"><table><thead><tr><th>Worker ID</th><th>Ward</th><th>Task</th><th>Shift</th><th>Reports</th><th>Last report</th><th>Open cases</th><th></th></tr></thead><tbody>
              {data.items.map((w) => <tr key={w.id}><td><button className="btn sm" onClick={() => setDetail(w.id)}>{w.pseudo_id}</button> {w.is_synthetic && <SyntheticTag />} {!w.active && <span className="chip">Inactive</span>}</td><td>{w.ward}</td><td>{w.task}</td><td>{w.shift_type}</td><td>{w.report_count}</td><td>{fmtDateTime(w.last_report_at)}</td><td>{w.open_cases}</td><td><button className="btn sm" onClick={() => open(w)}>Edit</button></td></tr>)}
            </tbody></table></div><Pager page={page} total={data.total} pageSize={15} onPage={setPage} /></>
          ))}
        </Async>
      </Card>
      {edit && (
        <Modal title={edit === "new" ? "Add worker" : "Edit worker"} onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Cancel</button><button className="btn primary" onClick={save} disabled={!form.ward_id || !form.task}>Save</button></>}>
          {edit === "new" && <Field label="Pseudonymous ID (optional)" hint="Leave empty to auto-generate"><input value={form.pseudo_id} onChange={(e) => setForm({ ...form, pseudo_id: e.target.value })} /></Field>}
          <Field label="Ward"><select value={form.ward_id} onChange={(e) => setForm({ ...form, ward_id: e.target.value })}><option value="">Choose…</option>{meta.wards.filter((w) => w.active).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></Field>
          <Field label="Task"><select value={form.task} onChange={(e) => setForm({ ...form, task: e.target.value })}><option value="">Choose…</option>{meta.tasks.map((x) => <option key={x}>{x}</option>)}</select></Field>
          <Field label="Usual shift"><select value={form.shift_type} onChange={(e) => setForm({ ...form, shift_type: e.target.value })}>{meta.shift_types.map((x) => <option key={x}>{x}</option>)}</select></Field>
          <label className="row"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />Active</label>
        </Modal>
      )}
      {detail && (
        <Modal wide title="Worker history" onClose={() => setDetail(null)}>
          <Async loading={det.loading} error={det.error} retry={det.reload}>{det.data && <>
            <p><strong>{det.data.pseudo_id}</strong> · {det.data.ward} · {det.data.task} · {det.data.shift_type} shift</p>
            <h3>Reports ({det.data.reports.length})</h3>
            {det.data.reports.length === 0 ? <Empty title="No reports yet" /> : <div className="tbl"><table><thead><tr><th>When</th><th>Region</th><th>Severity</th><th>Score</th><th>Case</th></tr></thead><tbody>{det.data.reports.map((r: Json) => <tr key={r.id}><td>{fmtDateTime(r.created_at)}</td><td>{r.body_region_label}</td><td>{r.severity}/10</td><td><LevelBadge level={r.risk_level} /> {r.risk_score}</td><td>{r.case_id ? <Link to={`/cases/${r.case_id}`}>Open</Link> : "—"}</td></tr>)}</tbody></table></div>}
            <h3>Interventions ({det.data.cases.length})</h3>
            {det.data.cases.length === 0 ? <p className="muted">None.</p> : <ul className="plain">{det.data.cases.map((c: Json) => <li key={c.id}><Link to={`/cases/${c.id}`}>{c.code}</Link> <StatusBadge status={c.status} /> {c.body_region_label} · owner {c.owner ?? "unassigned"}</li>)}</ul>}
            <div style={{ marginTop: 12 }}><Link className="btn primary" to="/reports/new">New report</Link></div>
          </>}</Async>
        </Modal>
      )}
    </>
  );
}
