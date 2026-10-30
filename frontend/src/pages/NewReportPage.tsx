import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { useLang } from "../i18n";
import { api, ApiError } from "../services/api";
import { Json, Page } from "../types";
import { validateReport } from "../utils/validate";
import { Async, Field, LevelBadge, Modal, PageHeader, useToast, Card } from "../components/ui/ui";

function YesNo({ value, onChange, yes, no }: { value: boolean; onChange: (v: boolean) => void; yes: string; no: string }) {
  return (
    <div className="yn">
      <button type="button" className={value ? "on" : ""} aria-pressed={value} onClick={() => onChange(true)}>{yes}</button>
      <button type="button" className={!value ? "on" : ""} aria-pressed={!value} onClick={() => onChange(false)}>{no}</button>
    </div>
  );
}

export default function NewReportPage() {
  const { meta } = useMeta();
  const { t, region, task, shift } = useLang();
  const toast = useToast();
  const workers = useApi<Page<Json>>("/workers?page_size=200&active=true");
  const [f, setF] = useState({ workerId: "", ward: "", task: "", region: "", severity: null as number | null, hours: "8", shift: "", rep: false, lift: false, desc: "" });
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [dup, setDup] = useState<string | null>(null);
  const [result, setResult] = useState<Json>(null);
  const set = (p: Partial<typeof f>) => setF((s) => ({ ...s, ...p }));
  const matched = workers.data?.items.find((w) => w.pseudo_id.toLowerCase() === f.workerId.trim().toLowerCase());

  useEffect(() => {
    if (matched) setF((s) => ({ ...s, ward: String(matched.ward_id), task: matched.task, shift: matched.shift_type }));
  }, [matched?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(allow = false) {
    const e = validateReport({ workerId: f.workerId, ward: f.ward, task: f.task, region: f.region, severity: f.severity, hours: f.hours, shift: f.shift });
    const out: Record<string, string> = {};
    Object.entries(e).forEach(([k, v]) => { out[k] = t(v as never); });
    if (f.workerId.trim() && !matched) out.workerId = t("err_worker");
    setErrs(out);
    if (Object.keys(out).length || !matched) return;
    setBusy(true);
    try {
      const r = await api.post<Json>("/reports", { worker_id: matched.id, ward_id: Number(f.ward), task: f.task, body_region: f.region, severity: f.severity, shift_hours: Number(f.hours), shift_type: f.shift, repetitive: f.rep, frequent_lifting: f.lift, description: f.desc.trim() || null, allow_duplicate: allow });
      setDup(null);
      setResult(r);
      toast("Report saved");
    } catch (err) {
      const ae = err as ApiError;
      const d = ae.detail as { code?: string } | string;
      if (ae.status === 409 && typeof d === "object" && d?.code === "possible_duplicate") setDup(ae.message);
      else toast(ae.message, "err");
    } finally { setBusy(false); }
  }

  if (result) {
    const r = result.report, risk = result.risk;
    return (
      <div className="big-form">
        <PageHeader title={t("thanks_title")} subtitle={t("thanks_body")} />
        <Card title={t("assessment")}>
          <div className="row"><strong>{t("score")}: {risk.score}/100</strong><span>{t("level")}:</span><LevelBadge level={risk.level} /></div>
          <h3>{t("why_score")}</h3>
          <ul className="plain contrib">{risk.contributions.map((c: Json, i: number) => <li key={i}><span>{c.detail}</span><strong>+{c.points}</strong></li>)}</ul>
          {risk.notes.map((n: string, i: number) => <p key={i} className="warn-box">{n}</p>)}
          <p className="muted small">An operational priority score for review. It is not a medical diagnosis or an injury probability.</p>
          {result.note && <p className="warn-box">{result.note}</p>}
          <div className="row" style={{ marginTop: 12 }}>
            <span className="chip">Saved as report #{r.id}</span>
            {result.alert && <span className="chip warn">Alert #{result.alert.id} created</span>}
            {result.case && <Link className="btn" to={`/cases/${result.case.id}`}>{t("view_case")} {result.case.code}</Link>}
            <Link className="btn" to="/reports">{t("view_record")}</Link>
            <button className="btn primary" onClick={() => { setResult(null); setF({ ...f, severity: null, desc: "", region: "" }); }}>{t("another")}</button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="big-form">
      <PageHeader title={t("form_title")} subtitle={t("form_intro")} />
      <Async loading={workers.loading} error={workers.error} retry={workers.reload}>
        <Card>
          <Field label={t("worker_id")} error={errs.workerId} hint={matched ? `${matched.ward} · ${task(matched.task)}` : "e.g. SW-0001"}>
            <input list="worker-ids" value={f.workerId} onChange={(e) => set({ workerId: e.target.value })} autoComplete="off" />
            <datalist id="worker-ids">{workers.data?.items.map((w) => <option key={w.id} value={w.pseudo_id} />)}</datalist>
          </Field>
          <div className="formgrid">
            <Field label={t("ward")} error={errs.ward}>
              <select value={f.ward} onChange={(e) => set({ ward: e.target.value })}>
                <option value="">{t("choose")}</option>{meta.wards.filter((w) => w.active).map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </Field>
            <Field label={t("task")} error={errs.task}>
              <select value={f.task} onChange={(e) => set({ task: e.target.value })}>
                <option value="">{t("choose")}</option>{meta.tasks.map((x) => <option key={x} value={x}>{task(x)}</option>)}
              </select>
            </Field>
          </div>
          <Field label={t("body_region")} error={errs.region}>
            <div className="choice" role="radiogroup">
              {meta.body_regions.map((r) => <button type="button" key={r.key} role="radio" aria-checked={f.region === r.key} className={f.region === r.key ? "on" : ""} onClick={() => set({ region: r.key })}>{region(r.key, r.label)}</button>)}
            </div>
          </Field>
          <Field label={t("discomfort")} error={errs.severity}>
            <div className="scale" role="radiogroup">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => <button type="button" key={n} role="radio" aria-checked={f.severity === n} className={f.severity === n ? "on" : ""} onClick={() => set({ severity: n })}>{n}</button>)}
            </div>
            <span className="muted small">1–3 {t("mild")} · 4–6 {t("moderate_l")} · 7–10 {t("severe")}</span>
          </Field>
          <div className="formgrid">
            <Field label={t("shift_hours")} error={errs.hours}><input type="number" min={1} max={16} step={0.5} inputMode="decimal" value={f.hours} onChange={(e) => set({ hours: e.target.value })} /></Field>
            <Field label={t("shift_type")} error={errs.shift}>
              <select value={f.shift} onChange={(e) => set({ shift: e.target.value })}>
                <option value="">{t("choose")}</option>{meta.shift_types.map((s) => <option key={s} value={s}>{shift(s)}</option>)}
              </select>
            </Field>
          </div>
          <Field label={t("repetitive")}><YesNo value={f.rep} onChange={(v) => set({ rep: v })} yes={t("yes")} no={t("no")} /></Field>
          <Field label={t("lifting")}><YesNo value={f.lift} onChange={(v) => set({ lift: v })} yes={t("yes")} no={t("no")} /></Field>
          <Field label={t("description")}><textarea maxLength={500} value={f.desc} onChange={(e) => set({ desc: e.target.value })} /></Field>
          <button className="btn primary lg" disabled={busy} onClick={() => submit(false)}>{busy ? t("sending") : t("submit")}</button>
        </Card>
      </Async>
      {dup && (
        <Modal title={t("dup_title")} onClose={() => setDup(null)} footer={<><button className="btn" onClick={() => setDup(null)}>{t("cancel")}</button><button className="btn primary" onClick={() => submit(true)}>{t("send_anyway")}</button></>}>
          <p>{t("dup_body")}</p><p className="muted small">{dup}</p>
        </Modal>
      )}
    </div>
  );
}
