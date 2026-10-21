import { useEffect, useState } from "react";
import { api, ApiError, type Store, type StoreItem, type StoreType } from "../api";
import { ErrorBox, ItemImage, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { StorePicker, WithStore } from "./common";
import { rupeesToPaise } from "./reminder";

type CatalogItem = { id: number; name: string; name_hi: string | null; image_path: string | null; pack_sizes: string | null };

function ItemRow({ storeId, item, onSaved }: { storeId: number; item: StoreItem; onSaved: () => void }) {
  const { t, lang } = useApp();
  const [price, setPrice] = useState(String(item.price_paise / 100));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const label = lang === "hi" && item.name_hi ? item.name_hi : item.name;
  const dirty = rupeesToPaise(price) !== item.price_paise;

  async function save(available: boolean) {
    const paise = rupeesToPaise(price);
    if (!paise) { setError(t("price")); return; }
    setBusy(true); setError(null);
    try { await api(`/merchant/stores/${storeId}/items/${item.id}`, { method: "PATCH", body: { price_paise: paise, available } }); onSaved(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); } finally { setBusy(false); }
  }

  return (
    <li className="card space-y-2 p-3">
      <div className="flex items-center gap-3">
        <ItemImage path={item.image_path} alt={label} size={52} />
        <p className="min-w-0 flex-1 font-semibold leading-tight">{label}</p>
        <button className={`btn !min-h-10 ${item.available ? "btn-primary" : "btn-ghost"}`} disabled={busy} onClick={() => void save(!item.available)} aria-pressed={item.available}>
          {item.available ? t("inStock") : t("outOfStock")}
        </button>
      </div>
      <div className="flex items-center gap-2">
        <input className="input" inputMode="decimal" aria-label={t("price")} value={price} onChange={(e) => setPrice(e.target.value)} />
        <button className="btn btn-primary" disabled={busy || !dirty} onClick={() => void save(item.available)}>{t("save")}</button>
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
    </li>
  );
}

function CatalogAdder({ store, listedIds, onAdded }: { store: Store; listedIds: Set<number>; onAdded: () => void }) {
  const { t, lang } = useApp();
  const types = useFetch<StoreType[]>("/store-types");
  const code = types.data?.find((x) => x.id === store.store_type_id)?.code;
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [prices, setPrices] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const h = window.setTimeout(() => setDebounced(q.trim()), 300); return () => window.clearTimeout(h); }, [q]);
  const res = useFetch<CatalogItem[]>(code ? `/catalog/items?store_type=${code}&limit=60${debounced ? `&q=${encodeURIComponent(debounced)}` : ""}` : null);

  async function add(c: CatalogItem) {
    const paise = rupeesToPaise(prices[c.id] ?? "");
    if (!paise) { setError(t("price")); return; }
    setError(null);
    try { await api(`/merchant/stores/${store.id}/catalog/${c.id}`, { method: "PUT", body: { price_paise: paise, available: true } }); onAdded(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }

  return (
    <div className="space-y-3">
      <input className="input" type="search" placeholder={t("searchPlaceholder")} value={q} onChange={(e) => setQ(e.target.value)} />
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      {res.loading ? <Spinner /> : (
        <ul className="space-y-2">
          {(res.data ?? []).map((c) => {
            const name = lang === "hi" && c.name_hi ? c.name_hi : c.name;
            const listed = listedIds.has(c.id);
            return (
              <li key={c.id} className="card flex items-center gap-2 p-2">
                <ItemImage path={c.image_path} alt={name} size={44} />
                <div className="min-w-0 flex-1"><p className="font-semibold leading-tight">{name}</p>{c.pack_sizes && <p className="truncate text-xs text-gray-500">{c.pack_sizes}</p>}</div>
                {listed ? <span className="text-sm text-gray-500">{t("listed")}</span> : (
                  <>
                    <input className="input !w-24" inputMode="decimal" placeholder="₹" aria-label={t("price")} value={prices[c.id] ?? ""} onChange={(e) => setPrices((p) => ({ ...p, [c.id]: e.target.value }))} />
                    <button className="btn btn-primary !px-3" onClick={() => void add(c)}>{t("add2")}</button>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function CustomAdder({ storeId, onAdded }: { storeId: number; onAdded: () => void }) {
  const { t } = useApp();
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function add() {
    const paise = rupeesToPaise(price);
    if (name.trim().length < 2 || !paise) { setError(`${t("itemName")} / ${t("price")}`); return; }
    setError(null);
    try { await api(`/merchant/stores/${storeId}/custom-items`, { method: "POST", body: { name: name.trim(), price_paise: paise } }); setName(""); setPrice(""); onAdded(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }
  return (
    <div className="space-y-2">
      <input className="input" placeholder={t("itemName")} value={name} onChange={(e) => setName(e.target.value)} />
      <div className="flex gap-2">
        <input className="input" inputMode="decimal" placeholder={t("price")} value={price} onChange={(e) => setPrice(e.target.value)} />
        <button className="btn btn-primary" onClick={() => void add()}>{t("add2")}</button>
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
    </div>
  );
}

function ItemsBody({ store, stores, pick }: { store: Store; stores: Store[]; pick: (id: number) => void }) {
  const { t } = useApp();
  const items = useFetch<StoreItem[]>(`/stores/${store.id}/items`);
  const [panel, setPanel] = useState<"catalog" | "custom" | null>(null);
  if (items.loading) return <Spinner />;
  if (items.error || !items.data) return <ErrorBox message={items.error ?? "error"} onRetry={items.reload} />;
  const listed = new Set(items.data.map((i) => i.catalog_item_id).filter((x): x is number => x !== null));
  const toggle = (p: "catalog" | "custom") => setPanel(panel === p ? null : p);

  return (
    <section className="space-y-3">
      <StorePicker stores={stores} store={store} onPick={pick} />
      <div className="flex gap-2">
        <button className={`btn flex-1 ${panel === "catalog" ? "btn-primary" : "btn-ghost"}`} onClick={() => toggle("catalog")}>{t("addFromCatalog")}</button>
        <button className={`btn flex-1 ${panel === "custom" ? "btn-primary" : "btn-ghost"}`} onClick={() => toggle("custom")}>{t("addMyOwn")}</button>
      </div>
      {panel === "catalog" && <CatalogAdder store={store} listedIds={listed} onAdded={items.reload} />}
      {panel === "custom" && <CustomAdder storeId={store.id} onAdded={items.reload} />}
      {items.data.length === 0 ? <p className="py-6 text-center text-gray-500">{t("noItems")}</p> : (
        <ul className="space-y-2">{items.data.map((i) => <ItemRow key={`${i.id}-${i.price_paise}-${i.available}`} storeId={store.id} item={i} onSaved={items.reload} />)}</ul>
      )}
    </section>
  );
}

export default function MerchantItems() {
  return <WithStore>{({ store, stores, pick }) => <ItemsBody store={store} stores={stores} pick={pick} />}</WithStore>;
}
