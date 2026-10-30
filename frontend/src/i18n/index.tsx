import { createContext, ReactNode, useCallback, useContext, useState } from "react";
import { en, Key } from "./en";
import { ta, taLabels } from "./ta";

export type Lang = "en" | "ta";
interface Ctx { lang: Lang; setLang: (l: Lang) => void; t: (k: Key) => string; task: (n: string) => string; region: (k: string, fallback?: string) => string; shift: (n: string) => string }
const LangCtx = createContext<Ctx>(null as unknown as Ctx);

function initial(): Lang {
  try { return localStorage.getItem("safeloop_lang") === "ta" ? "ta" : "en"; } catch { return "en"; }
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, set] = useState<Lang>(initial);
  const setLang = useCallback((l: Lang) => { set(l); try { localStorage.setItem("safeloop_lang", l); } catch { /* ignore */ } document.documentElement.lang = l; }, []);
  const ta_ = lang === "ta";
  const value: Ctx = {
    lang, setLang,
    t: (k) => (ta_ ? ta[k] : en[k]) ?? en[k],
    task: (n) => (ta_ ? taLabels.tasks[n] ?? n : n),
    region: (k, fb) => (ta_ ? taLabels.regions[k] ?? fb ?? k : fb ?? k),
    shift: (n) => (ta_ ? taLabels.shifts[n] ?? n : n),
  };
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>;
}
export const useLang = () => useContext(LangCtx);
