import { createContext, ReactNode, useContext } from "react";
import { useApi } from "./useApi";
import { Meta } from "../types";
import { ErrorBox, Loading } from "../components/ui/ui";

interface MetaCtx { meta: Meta; reload: () => void }
const Ctx = createContext<MetaCtx>(null as unknown as MetaCtx);
export const useMeta = () => useContext(Ctx);

export function MetaProvider({ children }: { children: ReactNode }) {
  const { data, loading, error, reload } = useApi<Meta>("/meta");
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} retry={reload} />;
  return <Ctx.Provider value={{ meta: data, reload }}>{children}</Ctx.Provider>;
}
