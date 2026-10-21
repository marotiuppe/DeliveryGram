import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { SearchHit } from "../api";
import { ErrorBox, ItemImage, Price, Section, Spinner, Stepper } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

export default function Search() {
  const { t, lang, villageId, cart, addToCart, setQty } = useApp();
  const [params, setParams] = useSearchParams();
  const [text, setText] = useState(params.get("q") ?? "");
  const [q, setQ] = useState(text.trim());

  useEffect(() => {
    const h = window.setTimeout(() => { setQ(text.trim()); setParams(text.trim() ? { q: text.trim() } : {}, { replace: true }); }, 350);
    return () => window.clearTimeout(h);
  }, [text, setParams]);

  const path = q.length >= 2 ? `/search/items?q=${encodeURIComponent(q)}${villageId ? `&village_id=${villageId}` : ""}` : null;
  const res = useFetch<SearchHit[]>(path);

  return (
    <Section title={t("search")}>
      <input className="input" type="search" autoFocus placeholder={t("searchPlaceholder")} value={text} onChange={(e) => setText(e.target.value)} />
      {!path ? <p className="text-gray-500">{t("searchHint")}</p> : res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : (res.data ?? []).length === 0 ? (
        <p className="py-6 text-center text-gray-500">{t("noResults")}</p>
      ) : (
        <ul className="space-y-3">
          {(res.data ?? []).map((h, idx) => {
            const name = lang === "hi" && h.name_hi ? h.name_hi : h.name;
            const inCart = cart.find((l) => l.storeItemId === h.store_item_id);
            return (
              <li key={h.store_item_id} className="card flex items-center gap-3 p-3">
                <ItemImage path={h.image_path} alt={name} />
                <div className="min-w-0 flex-1">
                  <p className="font-semibold leading-tight">{name}</p>
                  <p className="text-sm text-gray-600">{t("fromShop")} {h.store_name}</p>
                  <p><Price paise={h.price_paise} /> {idx === 0 && (res.data ?? []).length > 1 && <span className="ml-1 rounded bg-green-100 px-2 text-xs font-bold text-green-800">{t("cheapest")}</span>}</p>
                  {h.requires_prescription && <p className="text-xs text-red-700">{t("rxBlocked")}</p>}
                </div>
                {h.requires_prescription ? null : inCart ? <Stepper qty={inCart.qty} onChange={(n) => setQty(h.store_item_id, n)} /> : (
                  <button className="btn btn-primary" onClick={() => addToCart({ storeItemId: h.store_item_id, storeId: h.store_id, storeName: h.store_name, name: h.name, nameHi: h.name_hi, pricePaise: h.price_paise, imagePath: h.image_path })}>{t("add")}</button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}
