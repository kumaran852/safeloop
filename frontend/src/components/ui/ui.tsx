import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { X } from "lucide-react";

/* ---------- toast ---------- */
interface Toast { id: number; msg: string; kind: "ok" | "err" }
const ToastCtx = createContext<(msg: string, kind?: "ok" | "err") => void>(() => undefined);
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((msg: string, kind: "ok" | "err" = "ok") => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, msg, kind }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => <div key={t.id} className={`toast ${t.kind}`}>{t.msg}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}

/* ---------- badges ---------- */
export const LevelBadge = ({ level }: { level: string }) => <span className={`badge lvl-${level}`}>{level}</span>;
export const StatusBadge = ({ status }: { status: string }) => <span className={`badge st-${status.replace(/\s/g, "")}`}>{status}</span>;
export const Chip = ({ children, tone }: { children: ReactNode; tone?: "warn" | "danger" | "info" }) => <span className={`chip ${tone ?? ""}`}>{children}</span>;
export const SyntheticTag = () => <span className="chip info" title="Synthetic demonstration data">Demo</span>;

/* ---------- layout bits ---------- */
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div><h1>{title}</h1>{subtitle && <p className="muted">{subtitle}</p>}</div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}
export function Card({ title, actions, children, className }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className ?? ""}`}>
      {(title || actions) && <header className="card-head"><h2>{title}</h2>{actions}</header>}
      {children}
    </section>
  );
}
export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: string; tone?: "warn" | "danger" }) {
  return <div className={`stat ${tone ?? ""}`}><div className="stat-label">{label}</div><div className="stat-value">{value}</div>{sub && <div className="stat-sub">{sub}</div>}</div>;
}

/* ---------- states ---------- */
export const Spinner = () => <div className="spinner" role="progressbar" aria-label="Loading" />;
export const Loading = () => <div className="state"><Spinner /><span className="muted">Loading…</span></div>;
export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="state err" role="alert"><strong>Something went wrong</strong><span>{message}</span>{retry && <button className="btn" onClick={retry}>Try again</button>}</div>;
}
export function Empty({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return <div className="state"><strong>{title}</strong>{hint && <span className="muted">{hint}</span>}{action}</div>;
}
export function Async({ loading, error, retry, children }: { loading: boolean; error: string | null; retry?: () => void; children: ReactNode }) {
  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} retry={retry} />;
  return <>{children}</>;
}

/* ---------- modal ---------- */
export function Modal({ title, onClose, children, footer, wide }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <header className="card-head"><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button></header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-foot">{footer}</footer>}
      </div>
    </div>
  );
}

/* ---------- form + pager ---------- */
export function Field({ label, error, children, hint }: { label: string; error?: string; children: ReactNode; hint?: string }) {
  return <label className="field"><span className="field-label">{label}</span>{children}{hint && <span className="muted small">{hint}</span>}{error && <span className="field-err" role="alert">{error}</span>}</label>;
}
export function Pager({ page, total, pageSize, onPage }: { page: number; total: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pager">
      <span className="muted small">{total} record{total === 1 ? "" : "s"}</span>
      <div className="row">
        <button className="btn sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
        <span className="small">Page {page} of {pages}</span>
        <button className="btn sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}
export function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => { const h = setTimeout(() => setV(value), ms); return () => clearTimeout(h); }, [value, ms]);
  return v;
}
