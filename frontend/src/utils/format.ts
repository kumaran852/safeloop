export function parseUtc(s?: string | null): Date | null {
  if (!s) return null;
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(s) ? s : s.length <= 10 ? s : s + "Z");
}
export function fmtDateTime(s?: string | null): string {
  const d = parseUtc(s);
  return d ? d.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
}
export function fmtDate(s?: string | null): string {
  const d = parseUtc(s);
  return d ? d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
export const pct = (r?: { num: number; den: number; pct: number | null } | null) => (r && r.pct !== null ? `${r.pct}% (${r.num}/${r.den})` : "n/a (no eligible cases)");
export const hrs = (s?: { available: boolean; n: number; median_hours: number | null } | null) => (s && s.available ? `${s.median_hours} h median (n=${s.n})` : "unavailable (no recorded timestamps)");
