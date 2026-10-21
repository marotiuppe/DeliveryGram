import { Link, useNavigate } from "react-router-dom";
import type { Village } from "../api";
import { cartSubtotal, formatMoney, groupByShop } from "../cart";
import { ItemImage, Price, Section, Stepper } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

export default function Cart() {
  const { t, lang, cart, setQty, villageId } = useApp();
  const nav = useNavigate();
  const villages = useFetch<Village[]>("/villages");
  const village = villages.data?.find((v) => v.id === villageId);

  if (cart.length === 0) {
    return (
      <Section title={t("cart")}>
        <div className="card space-y-3 p-6 text-center"><p>{t("cartEmpty")}</p><Link className="btn btn-primary" to="/">{t("browseShops")}</Link></div>
      </Section>
    );
  }
  const groups = groupByShop(cart);
  const fee = village?.delivery_fee_paise ?? 0;
  const subtotal = cartSubtotal(cart);
  const min = village?.min_order_paise ?? 0;
  const belowMin = subtotal < min;

  return (
    <Section title={t("cart")}>
      <p className="rounded-xl bg-brand-soft p-3 text-sm">{t("oneDelivery")}</p>
      {groups.map((g) => (
        <div key={g.storeId} className="card space-y-3 p-3">
          <div className="flex items-center justify-between">
            <Link to={`/shop/${g.storeId}`} className="font-bold text-brand">{g.storeName}</Link>
            <span className="text-sm text-muted">{t("bill")}: <Price paise={g.subtotalPaise} /></span>
          </div>
          {g.lines.map((l) => (
            <div key={l.storeItemId} className="flex items-center gap-3">
              <ItemImage path={l.imagePath} alt={l.name} size={48} />
              <div className="min-w-0 flex-1"><p className="font-semibold leading-tight">{lang === "hi" && l.nameHi ? l.nameHi : l.name}</p><p className="text-sm">{formatMoney(l.pricePaise)}</p></div>
              <Stepper qty={l.qty} onChange={(n) => setQty(l.storeItemId, n)} />
            </div>
          ))}
        </div>
      ))}
      <div className="card space-y-1 p-4">
        <div className="flex justify-between"><span>{t("total")}</span><Price paise={subtotal} /></div>
        {village && <div className="flex justify-between text-sm text-muted"><span>{t("deliveryFee")}</span><span>{formatMoney(fee)}</span></div>}
        <div className="flex justify-between border-t pt-2 text-lg"><span className="font-bold">{t("grandTotal")}</span><Price paise={subtotal + fee} /></div>
      </div>
      {belowMin && <p role="alert" className="text-sm font-semibold text-red-700">{t("minOrder")}: {formatMoney(min)}</p>}
      <button className="btn btn-primary w-full" disabled={belowMin} onClick={() => nav("/checkout")}>{t("checkout")}</button>
    </Section>
  );
}
