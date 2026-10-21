import { useState } from "react";
import { Link } from "react-router-dom";
import type { Store, StoreType, Village } from "../api";
import { ErrorBox, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

export function VillagePicker({ villages }: { villages: Village[] }) {
  const { t, setVillageId } = useApp();
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-extrabold">{t("chooseVillage")}</h1>
      {villages.map((v) => (
        <button key={v.id} className="card w-full p-4 text-left text-lg font-bold" onClick={() => setVillageId(v.id)}>
          {v.name}{v.district ? <span className="block text-sm font-normal text-muted">{v.district}</span> : null}
        </button>
      ))}
    </section>
  );
}

export default function Home() {
  const { t, lang, villageId, setVillageId } = useApp();
  const villages = useFetch<Village[]>("/villages");
  const types = useFetch<StoreType[]>("/store-types");
  const stores = useFetch<Store[]>(villageId ? `/stores?village_id=${villageId}` : null);
  const [typeId, setTypeId] = useState<number | null>(null);

  if (villages.loading) return <Spinner />;
  if (villages.error || !villages.data) return <ErrorBox message={villages.error ?? "error"} onRetry={villages.reload} />;
  const village = villages.data.find((v) => v.id === villageId);
  if (!village) return <VillagePicker villages={villages.data} />;

  const typeName = (id: number) => {
    const ty = types.data?.find((x) => x.id === id);
    return ty ? (lang === "hi" && ty.name_hi ? ty.name_hi : ty.name) : "";
  };
  const shown = (stores.data ?? []).filter((s) => typeId === null || s.store_type_id === typeId);
  const usedTypes = (types.data ?? []).filter((ty) => stores.data?.some((s) => s.store_type_id === ty.id));

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-2xl font-extrabold"><span aria-hidden>📍</span>{village.name}</h1>
        <button className="text-sm font-semibold text-brand underline" onClick={() => setVillageId(0)}>{t("village")}</button>
      </div>
      <div className="chips -mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {[{ id: null as number | null, label: t("allShops") }, ...usedTypes.map((ty) => ({ id: ty.id as number | null, label: lang === "hi" && ty.name_hi ? ty.name_hi : ty.name }))].map((c) => (
          <button key={String(c.id)} onClick={() => setTypeId(c.id)}
            className={`shrink-0 rounded-full px-4 py-2 font-semibold ${typeId === c.id ? "bg-brand text-white shadow" : "border border-gray-300 bg-white text-ink"}`}>{c.label}</button>
        ))}
      </div>
      {stores.loading ? <Spinner /> : stores.error ? <ErrorBox message={stores.error} onRetry={stores.reload} /> : shown.length === 0 ? (
        <p className="py-8 text-center text-muted">{t("noShops")}</p>
      ) : (
        <ul className="space-y-3">
          {shown.map((s) => (
            <li key={s.id}>
              <Link to={`/shop/${s.id}`} className="card flex items-center justify-between gap-3 p-4">
                <span aria-hidden className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-xl font-extrabold text-brand-dark">{s.name.trim().charAt(0).toUpperCase()}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-lg font-bold">{s.name}</p>
                  <p className="text-sm text-muted">{typeName(s.store_type_id)}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-sm font-bold ${s.is_open ? "bg-green-100 text-green-800" : "bg-gray-200 text-muted"}`}>{s.is_open ? t("open") : t("closed")}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
