import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { useLang } from "../i18n";
import { api } from "../services/api";
import { Json } from "../types";
import { Async, Card, Chip, Field, Modal, PageHeader, useToast } from "../components/ui/ui";

export default function SettingsPage() {
  const { lang, setLang, t } = useLang();
  const { meta, reload: reloadMeta } = useMeta();
  const toast = useToast();
  const { data: s, loading, error, reload } = useApi<Json>("/settings");
  const [th, setTh] = useState({ moderate: 30, high: 50, critical: 70 });
  const [pat, setPat] = useState({ window_days: 30, min_reports: 3, min_workers: 2 });
  const [tasks, setTasks] = useState("");
  const [ward, setWard] = useState({ code: "", name: "" });
  const [reset, setReset] = useState<{ text: string; demo: boolean } | null>(null);
  useEffect(() => { if (s) { setTh(s.thresholds); setPat(s.pattern); setTasks(s.tasks.join("\n")); } }, [s]);

  async function put(body: Json, ok: string) {
    try { await api.put("/settings", body); toast(ok); reload(); reloadMeta(); } catch (e) { toast((e as Error).message, "err"); }
  }
  async function addWard() {
    try { await api.post("/wards", ward); toast("Ward added"); setWard({ code: "", name: "" }); reloadMeta(); } catch (e) { toast((e as Error).message, "err"); }
  }
  async function toggleWard(id: number, active: boolean) {
    try { await api.patch(`/wards/${id}`, { active }); reloadMeta(); } catch (e) { toast((e as Error).message, "err"); }
  }
  async function doReset() {
    try { await api.post("/admin/reset", { confirm: reset!.text, demo: reset!.demo }); toast("Database reset"); setReset(null); reload(); reloadMeta(); } catch (e) { toast((e as Error).message, "err"); }
  }
  return (
    <>
      <PageHeader title={t("nav_settings")} />
      <Async loading={loading} error={error} retry={reload}>{s && <>
        <div className="grid g2">
          <Card title="Language">
            <div className="seg"><button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>English</button><button className={lang === "ta" ? "on" : ""} onClick={() => setLang("ta")}>தமிழ்</button></div>
            <p className="muted small">Applies to the worker reporting form and navigation. Operator screens are English-only in this prototype.</p>
          </Card>
          <Card title="Demo data indicator">
            <p><Chip tone="info">{s.demo.synthetic_reports} synthetic reports</Chip> <Chip>{s.demo.observed_reports} observed reports</Chip> <Chip>{s.demo.workers} workers</Chip> <Chip>{s.demo.cases} cases</Chip></p>
            <p className="muted small">Seeded records are synthetic and tagged “Demo”. Reports submitted through the form are stored as observed records. Database file: <code>{s.database}</code></p>
          </Card>
          <Card title="Risk thresholds (operational priority)">
            <div className="formgrid">{(["moderate", "high", "critical"] as const).map((k) => <Field key={k} label={`${k[0].toUpperCase()}${k.slice(1)} from score`}><input type="number" min={1} max={100} value={th[k]} onChange={(e) => setTh({ ...th, [k]: Number(e.target.value) })} /></Field>)}</div>
            <button className="btn primary" onClick={() => put({ thresholds: th }, "Thresholds saved")}>Save thresholds</button>
            <p className="muted small">Applies to new reports only. Existing scores are not recalculated. Thresholds are configurable operational settings, not clinically validated cut-offs.</p>
          </Card>
          <Card title="Pattern detection rules">
            <div className="formgrid">
              <Field label="Window (days)"><input type="number" value={pat.window_days} onChange={(e) => setPat({ ...pat, window_days: Number(e.target.value) })} /></Field>
              <Field label="Minimum reports"><input type="number" min={2} value={pat.min_reports} onChange={(e) => setPat({ ...pat, min_reports: Number(e.target.value) })} /></Field>
              <Field label="Minimum workers"><input type="number" min={2} value={pat.min_workers} onChange={(e) => setPat({ ...pat, min_workers: Number(e.target.value) })} /></Field>
            </div>
            <button className="btn primary" onClick={() => put({ pattern: pat }, "Pattern rules saved")}>Save rules</button>
          </Card>
          <Card title="Tasks">
            <Field label="One task per line"><textarea value={tasks} onChange={(e) => setTasks(e.target.value)} /></Field>
            <button className="btn primary" onClick={() => put({ tasks: tasks.split("\n").map((x) => x.trim()).filter(Boolean) }, "Tasks saved")}>Save tasks</button>
          </Card>
          <Card title="Wards">
            <ul className="plain">{meta.wards.map((w) => <li key={w.id} className="row" style={{ marginBottom: 6 }}><span>{w.code} · {w.name}</span>{!w.active && <Chip>Inactive</Chip>}<button className="btn sm" onClick={() => toggleWard(w.id, !w.active)}>{w.active ? "Deactivate" : "Activate"}</button></li>)}</ul>
            <div className="formgrid"><Field label="Code"><input value={ward.code} onChange={(e) => setWard({ ...ward, code: e.target.value })} /></Field><Field label="Name"><input value={ward.name} onChange={(e) => setWard({ ...ward, name: e.target.value })} /></Field></div>
            <button className="btn" disabled={ward.code.length < 2 || ward.name.length < 2} onClick={addWard}>Add ward</button>
          </Card>
        </div>
        <Card title="Methodology and limitations">
          <p>The score (0–100) is the sum of transparent points: discomfort × {s.weights.severity_per_point}; repetitive movements +{s.weights.repetitive}; frequent lifting +{s.weights.frequent_lifting}; shift of 10 h or more +{s.weights.shift_10h} (8 h or more +{s.weights.shift_8h}); earlier reports by the same worker for the same body region +{s.weights.prior_report_each} each (max {s.weights.prior_report_max}); at least 2 reports from other workers in the same ward, task and region +{s.weights.peer_pattern}; earlier unverified case +{s.weights.unverified_case}. Discomfort of 8/10 or more is always at least High. Current thresholds: Moderate ≥ {s.thresholds.moderate}, High ≥ {s.thresholds.high}, Critical ≥ {s.thresholds.critical}.</p>
          <p className="muted">Weights and thresholds are unvalidated operational rules. The score is not a probability of injury, a diagnosis or a clinical risk measure, and no accuracy has been measured. No login is implemented: this prototype is not safe for real municipal records until authentication, authorisation, encryption and audit controls are added.</p>
        </Card>
        <Card title="Reset database">
          <p className="muted">Deletes all workers, reports, alerts, cases and settings, then optionally re-seeds the synthetic demo data.</p>
          <button className="btn danger" onClick={() => setReset({ text: "", demo: true })}>Reset database…</button>
        </Card>
        {reset && <Modal title="Confirm database reset" onClose={() => setReset(null)} footer={<><button className="btn" onClick={() => setReset(null)}>Cancel</button><button className="btn danger" disabled={reset.text !== "RESET"} onClick={doReset}>Reset now</button></>}>
          <p>This permanently deletes all current data. Type <strong>RESET</strong> to continue.</p>
          <Field label="Confirmation"><input value={reset.text} onChange={(e) => setReset({ ...reset, text: e.target.value })} /></Field>
          <label className="row"><input type="checkbox" checked={reset.demo} onChange={(e) => setReset({ ...reset, demo: e.target.checked })} />Re-seed synthetic demo data</label>
        </Modal>}
      </>}</Async>
    </>
  );
}
