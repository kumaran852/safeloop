export interface ReportDraft { workerId: string; ward: string; task: string; region: string; severity: number | null; hours: string; shift: string }
export type ErrKey = "err_worker" | "err_severity" | "err_hours" | "required";

export function validateReport(d: ReportDraft): Partial<Record<keyof ReportDraft, ErrKey>> {
  const e: Partial<Record<keyof ReportDraft, ErrKey>> = {};
  if (!d.workerId.trim()) e.workerId = "err_worker";
  if (!d.ward) e.ward = "required";
  if (!d.task) e.task = "required";
  if (!d.region) e.region = "required";
  if (!d.shift) e.shift = "required";
  if (d.severity === null || d.severity < 1 || d.severity > 10) e.severity = "err_severity";
  const h = Number(d.hours);
  if (!d.hours || Number.isNaN(h) || h < 1 || h > 16) e.hours = "err_hours";
  return e;
}
