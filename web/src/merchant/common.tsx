import { useEffect, useState } from "react";
import type { Store } from "../api";
import { ErrorBox, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

const KEY = "dg_merchant_store";

/** The shop the owner is working on. Most owners have one; the picker only shows for several. */
export function useMyStore() {
  const stores = useFetch<Store[]>("/merchant/stores");
  const [id, setId] = useState<number | null>(() => {
    try { const v = localStorage.getItem(KEY); return v ? Number(v) : null; } catch { return null; }
  });
  const list = stores.data ?? [];
  const store = list.find((s) => s.id === id) ?? list[0] ?? null;
  useEffect(() => { if (store) { try { localStorage.setItem(KEY, String(store.id)); } catch { /* ignore */ } } }, [store]);
  return { stores: list, store, setId, loading: stores.loading, error: stores.error, reload: stores.reload };
}

export function StorePicker({ stores, store, onPick }: { stores: Store[]; store: Store; onPick: (id: number) => void }) {
  const { t } = useApp();
  if (stores.length < 2) return <p className="text-lg font-bold text-brand">{store.name}</p>;
  return (
    <label className="block space-y-1">
      <span className="text-sm font-semibold">{t("chooseShop")}</span>
      <select className="input" value={store.id} onChange={(e) => onPick(Number(e.target.value))}>
        {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
    </label>
  );
}

/** Wraps a merchant screen: loads the owner's shop(s) and renders children with the chosen one. */
export function WithStore({ children }: { children: (s: { store: Store; stores: Store[]; pick: (id: number) => void; reloadStore: () => void }) => React.ReactNode }) {
  const m = useMyStore();
  const { t } = useApp();
  if (m.loading) return <Spinner />;
  if (m.error) return <ErrorBox message={m.error} onRetry={m.reload} />;
  if (!m.store) return <p className="card p-4 text-center">{t("noShops")}</p>;
  return <>{children({ store: m.store, stores: m.stores, pick: m.setId, reloadStore: m.reload })}</>;
}
