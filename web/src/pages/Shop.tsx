import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Store, StoreItem } from "../api";
import { ErrorBox, ItemImage, Price, Spinner, Stepper } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

export default function Shop() {
  const { id } = useParams();
  const { t, lang, cart, addToCart, setQty } = useApp();
  const store = useFetch<Store>(`/stores/${id}`);
  const items = useFetch<StoreItem[]>(`/stores/${id}/items`);
  const [q, setQ] = useState("");

  if (store.loading || items.loading) return <Spinner />;
  if (store.error || !store.data) return <ErrorBox message={store.error ?? "error"} onRetry={store.reload} />;
  if (items.error || !items.data) return <ErrorBox message={items.error ?? "error"} onRetry={items.reload} />;

  const s = store.data;
  const label = (i: StoreItem) => (lang === "hi" && i.name_hi ? i.name_hi : i.name);
  const needle = q.trim().toLowerCase();
  const shown = items.data.filter((i) => !needle || i.name.toLowerCase().includes(needle) || (i.name_hi ?? "").includes(needle));

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-extrabold">{s.name}</h1>
        {s.phone && <a href={`tel:${s.phone}`} className="inline-flex min-h-10 items-center text-sm font-bold text-brand underline">📞 {t("call")} {s.phone}</a>}
        {!s.is_open && <p className="mt-1 font-semibold text-red-700">{t("closed")}</p>}
      </div>
      <input className="input" type="search" placeholder={t("searchPlaceholder")} value={q} onChange={(e) => setQ(e.target.value)} />
      <ul className="space-y-3">
        {shown.map((i) => {
          const inCart = cart.find((l) => l.storeItemId === i.id);
          const blocked = i.requires_prescription; // prescription upload is not built yet
          const canBuy = s.is_open && i.available && !blocked;
          return (
            <li key={i.id} className="card flex items-center gap-3 p-3">
              <ItemImage path={i.image_path} alt={label(i)} />
              <div className="min-w-0 flex-1">
                <p className="font-semibold leading-tight">{label(i)} {i.requires_prescription && <span className="rounded bg-red-100 px-1.5 text-xs font-bold text-red-700">{t("rxBadge")}</span>}</p>
                <p><Price paise={i.price_paise} /></p>
                {blocked && <p className="text-xs text-red-700">{t("rxBlocked")}</p>}
              </div>
              {canBuy ? (
                inCart ? <Stepper qty={inCart.qty} onChange={(n) => setQty(i.id, n)} /> : (
                  <button className="btn btn-primary" onClick={() => addToCart({ storeItemId: i.id, storeId: s.id, storeName: s.name, name: i.name, nameHi: i.name_hi, pricePaise: i.price_paise, imagePath: i.image_path })}>{t("add")}</button>
                )
              ) : !blocked ? <span className="text-sm text-muted">{t("closed")}</span> : null}
            </li>
          );
        })}
      </ul>
      {shown.length === 0 && (
        <div className="card space-y-2 p-4 text-center">
          <p>{t("noResults")}</p>
          {needle.length >= 2 && <Link className="btn btn-primary" to={`/search?q=${encodeURIComponent(needle)}`}>{t("search")}: {needle}</Link>}
        </div>
      )}
      {needle.length >= 2 && shown.length > 0 && <Link className="block text-center font-semibold text-brand underline" to={`/search?q=${encodeURIComponent(needle)}`}>{t("search")}: {needle}</Link>}
    </section>
  );
}
