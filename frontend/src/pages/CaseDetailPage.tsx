import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import { Json } from "../types";
import { fmtDate, fmtDateTime } from "../utils/format";
import { Async, Card, Field, LevelBadge, Modal, PageHeader, StatusBadge, SyntheticTag, useToast } from "../components/ui/ui";

export default function CaseDetailPage() {
  const { id } = useParams();
  const { meta } = useMeta();
  const toast = useToast();
  const { data: c, loading, error, reload } = useApi<Json>(`/cases/${id}`);
  const [as, setAs] = useState<{ owner: string; due: string; priority: string; action: string } | null>(null);
  const [st, setSt] = useState<{ to: string; note: string; res: string } | null>(null);
  const [note, setNote] = useState("");
  const [fu, setFu] = useState({ outcome: "Improved", notes: "", evidence: "" });

  async function run(p: Promise<unknown>, ok: string, done?: () => void) {
    try { await p; toast(ok); done?.(); reload(); } catch (e) { toast((e as Error).message, "err"); }
  }
  const canFollow = c && ["In Progress", "Pending Verification", "Resolved"].includes(c.status);

  return (
    <Async loading={loading} error={error} retry={reload}>
      {c && <>
        <PageHeader title={`${c.code} · ${c.ward} · ${c.task}`} subtitle={`${c.body_region_label} · worker ${c.worker}`}
          actions={<><Link className="btn" to="/cases">Back to cases</Link><LevelBadge level={c.risk_level} /><StatusBadge status={c.status} />{c.report.is_synthetic && <SyntheticTag />}</>} />
        {c.status === "Reopened" && <p className="warn-box" style={{ marginBottom: 14 }}>This case was reopened. Reassign or restart work, then record a new follow-up.</p>}
        <div className="grid g2">
          <Card title="Case details" actions={c.status !== "Resolved" && <button className="btn sm" onClick={() => setAs({ owner: c.owner ?? "", due: c.due_date ?? "", priority: c.priority, action: c.recommended_action })}>{c.owner ? "Edit assignment" : "Assign owner"}</button>}>
            <table><tbody>
              <tr><th>Owner</th><td>{c.owner ?? <span className="chip danger">Unassigned</span>}</td></tr>
              <tr><th>Priority</th><td>{c.priority}</td></tr>
              <tr><th>Due date</th><td>{fmtDate(c.due_date)} {c.overdue && <span className="chip danger">Overdue</span>}</td></tr>
              <tr><th>Closure</th><td>{c.resolution_type === "verified_improvement" ? <span className="chip info">Verified improvement</span> : c.resolution_type === "administrative_closure" ? <span className="chip warn">Administrative closure (not verified)</span> : "Not closed"}</td></tr>
              <tr><th>Created / updated</th><td>{fmtDateTime(c.created_at)} / {fmtDateTime(c.updated_at)}</td></tr>
              <tr><th>Resolved</th><td>{fmtDateTime(c.resolved_at)}</td></tr>
              <tr><th>Source</th><td>Report #{c.report_id}{c.alert_id ? ` · alert #${c.alert_id}` : ""} (score {c.report.risk_score})</td></tr>
            </tbody></table>
            <h3>Why it was raised</h3><p className="note-box">{c.reason}</p>
            <h3>Recommended action</h3><p>{c.recommended_action}</p>
          </Card>
          <Card title="Workflow">
            <p className="muted small">Allowed next steps from <strong>{c.status}</strong>:</p>
            <div className="row" style={{ margin: "8px 0 14px" }}>
              {c.allowed_transitions.map((to: string) => <button key={to} className="btn" onClick={() => setSt({ to, note: "", res: to === "Resolved" ? "verified_improvement" : "" })}>{to}</button>)}
            </div>
            <h3>Add timeline note</h3>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} aria-label="Timeline note" />
            <button className="btn" disabled={note.trim().length < 2} onClick={() => run(api.post(`/cases/${id}/notes`, { note }), "Note added", () => setNote(""))}>Add note</button>
            <h3>Record follow-up observation</h3>
            {!canFollow ? <p className="muted small">Available once work has started.</p> : <>
              <Field label="Outcome"><select value={fu.outcome} onChange={(e) => setFu({ ...fu, outcome: e.target.value })}>{meta.outcomes.map((o) => <option key={o}>{o}</option>)}</select></Field>
              <Field label="Findings"><textarea value={fu.notes} onChange={(e) => setFu({ ...fu, notes: e.target.value })} /></Field>
              <Field label="Evidence (optional)"><input value={fu.evidence} onChange={(e) => setFu({ ...fu, evidence: e.target.value })} placeholder="e.g. site visit, worker check-in" /></Field>
              {fu.outcome !== "Improved" && ["Pending Verification", "Resolved"].includes(c.status) && <p className="warn-box">Recording “{fu.outcome}” will reopen this case automatically.</p>}
              <button className="btn primary" disabled={fu.notes.trim().length < 3} onClick={() => run(api.post(`/cases/${id}/follow-ups`, { outcome: fu.outcome, notes: fu.notes, evidence: fu.evidence || null }), "Follow-up recorded", () => setFu({ outcome: "Improved", notes: "", evidence: "" }))}>Record follow-up</button>
            </>}
          </Card>
        </div>
        <div className="grid g2" style={{ marginTop: 14 }}>
          <Card title={`Follow-up observations (${c.follow_ups.length})`}>
            {c.follow_ups.length === 0 ? <p className="muted">No follow-up recorded. Without one, closure cannot be verified.</p> : <ul className="plain">{c.follow_ups.map((f: Json) => <li key={f.id} style={{ marginBottom: 8 }}><span className={`chip ${f.outcome === "Improved" ? "info" : "danger"}`}>{f.outcome}</span> <span className="muted small">{fmtDateTime(f.observed_at)} · {f.recorded_by}</span><br />{f.notes}{f.evidence && <><br /><span className="muted small">Evidence: {f.evidence}</span></>}</li>)}</ul>}
          </Card>
          <Card title="Audit trail">
            <ul className="timeline">{c.events.map((e: Json) => <li key={e.id} className={e.actor === "system" ? "sys" : ""}>
              <strong>{e.event_type.replace("_", " ")}</strong>{e.to_status && <> · {e.from_status ? `${e.from_status} → ` : ""}{e.to_status}</>}
              <div className="muted small">{fmtDateTime(e.ts)} · {e.actor}</div>{e.note && <div>{e.note}</div>}</li>)}</ul>
          </Card>
        </div>
        {as && (
          <Modal title="Assign owner and due date" onClose={() => setAs(null)} footer={<><button className="btn" onClick={() => setAs(null)}>Cancel</button><button className="btn primary" disabled={as.owner.trim().length < 2} onClick={() => run(api.post(`/cases/${id}/assign`, { owner: as.owner, due_date: as.due || null, priority: as.priority, recommended_action: as.action }), "Assignment saved", () => setAs(null))}>Save</button></>}>
            <Field label="Owner (role or pseudonym)"><input value={as.owner} onChange={(e) => setAs({ ...as, owner: e.target.value })} placeholder="e.g. Ward Supervisor" /></Field>
            <Field label="Due date"><input type="date" value={as.due} onChange={(e) => setAs({ ...as, due: e.target.value })} /></Field>
            <Field label="Priority"><select value={as.priority} onChange={(e) => setAs({ ...as, priority: e.target.value })}>{["Low", "Medium", "High", "Urgent"].map((p) => <option key={p}>{p}</option>)}</select></Field>
            <Field label="Recommended preventive action"><textarea value={as.action} onChange={(e) => setAs({ ...as, action: e.target.value })} /></Field>
          </Modal>
        )}
        {st && (
          <Modal title={`Move to ${st.to}`} onClose={() => setSt(null)} footer={<><button className="btn" onClick={() => setSt(null)}>Cancel</button><button className="btn primary" onClick={() => run(api.post(`/cases/${id}/status`, { to_status: st.to, note: st.note || null, resolution_type: st.res || null }), `Status: ${st.to}`, () => setSt(null))}>Confirm</button></>}>
            {st.to === "Resolved" && <Field label="Closure type" hint="Verified improvement needs a latest follow-up of “Improved”.">
              <select value={st.res} onChange={(e) => setSt({ ...st, res: e.target.value })}><option value="verified_improvement">Verified improvement</option><option value="administrative_closure">Administrative closure (not verified)</option></select></Field>}
            <Field label={st.to === "Reopened" ? "Reason (required)" : "Note"}><textarea value={st.note} onChange={(e) => setSt({ ...st, note: e.target.value })} /></Field>
          </Modal>
        )}
      </>}
    </Async>
  );
}
