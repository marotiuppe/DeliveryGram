import { Link, useParams } from "react-router-dom";
import { api, type Delivery, type Order } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Section, Spinner, StatusChip } from "../components";
import { useApp } from "../state";
import type { Key } from "../i18n";
import { useFetch } from "../useFetch";

const deliveryTone = (s: string) => (s === "DELIVERED" ? "green" : s === "FAILED" || s === "CANCELLED" ? "red" : "amber") as "green" | "red" | "amber";

export function OrdersList({ base = "/orders", showPhone = false }: { base?: string; showPhone?: boolean }) {
  const { t } = useApp();
  const res = useFetch<Delivery[]>("/deliveries", 20000);
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  return (
    <Section title={t("myOrders")}>
      {res.data.length === 0 ? <p className="py-8 text-center text-gray-500">{t("noOrders")}</p> : (
        <ul className="space-y-3">
          {res.data.map((d) => (
            <li key={d.id}>
              <Link to={`${base}/${d.id}`} className="card block space-y-2 p-4">
                <div className="flex items-center justify-between"><span className="font-bold">#{d.id}</span><StatusChip text={t(`status${d.status}` as Key)} tone={deliveryTone(d.status)} /></div>
                {showPhone && <p className="text-sm font-semibold">{d.contact_phone}</p>}
                <p className="text-sm text-gray-600">{d.orders.map((o) => o.items.map((i) => i.name).join(", ")).join(" · ")}</p>
                <Price paise={d.grand_total_paise} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export function DeliveryDetail() {
  const { id } = useParams();
  const { t, me } = useApp();
  const res = useFetch<Delivery>(`/deliveries/${id}`, 15000);
  const stores = useFetch<{ id: number; name: string }[]>("/stores");
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  const d = res.data;
  const shopName = (sid: number) => stores.data?.find((s) => s.id === sid)?.name ?? `#${sid}`;

  async function cancel(o: Order) {
    try {
      await api(`/orders/${o.id}/status`, { method: "POST", body: { status: "CANCELLED" } });
      await res.reload();
    } catch { /* the bill may have been accepted meanwhile; the refresh below shows the real status */ await res.reload(); }
  }

  const active = d.status === "OPEN" || d.status === "OUT_FOR_DELIVERY";
  const hasRiderBill = d.orders.some((o) => o.fulfillment === "delivery" && !["REJECTED", "CANCELLED"].includes(o.status));
  return (
    <Section title={`${t("orders")} #${d.id}`}>
      <div className="flex items-center justify-between"><span>{t("status")}</span><StatusChip text={t(`status${d.status}` as Key)} tone={deliveryTone(d.status)} /></div>

      {d.delivery_code && active && (
        <div className="card space-y-1 border-2 border-brand p-4 text-center">
          <p className="font-semibold">{t("deliveryCode")}</p>
          <p className="text-5xl font-extrabold tracking-[0.3em] text-brand" aria-label={d.delivery_code.split("").join(" ")}>{d.delivery_code}</p>
          <p className="text-sm text-gray-600">{me?.role === "agent" ? `${t("tellCode")} (${d.contact_phone})` : t("deliveryCodeHelp")}</p>
        </div>
      )}

      {d.orders.map((o) => (
        <div key={o.id} className="card space-y-2 p-3">
          <div className="flex items-center justify-between">
            <p className="font-bold text-brand">{shopName(o.store_id)} <span className="text-sm font-normal text-gray-500">{t("bill")} #{o.id}</span></p>
            <StatusChip text={t(`order${o.status}` as Key)} tone={o.status === "DELIVERED" ? "green" : ["REJECTED", "CANCELLED", "FAILED"].includes(o.status) ? "red" : "amber"} />
          </div>
          {o.fulfillment === "pickup" && !["REJECTED", "CANCELLED", "DELIVERED"].includes(o.status) && (
            <p className="rounded-lg bg-brand-soft p-2 text-sm font-semibold">{o.status === "READY" ? t("readyCollect") : t("collectFromShop")}</p>
          )}
          <ul className="text-sm">{o.items.map((i) => <li key={i.store_item_id} className="flex justify-between"><span>{i.name} × {i.quantity}</span><span>{formatMoney(i.unit_price_paise * i.quantity)}</span></li>)}</ul>
          <div className="flex justify-between border-t pt-1"><span>{t("bill")} · {o.payment_method === "khata" ? t("payKhata") : o.payment_method === "upi" ? t("payUpi") : t("payCash")}</span><Price paise={o.total_paise} /></div>
          {(o.status === "PLACED" || o.status === "PENDING_PRESCRIPTION_REVIEW") && <button className="btn btn-ghost w-full" onClick={() => void cancel(o)}>{t("cancelBill")}</button>}
        </div>
      ))}

      <div className="card space-y-1 p-4">
        {hasRiderBill && <div className="flex justify-between text-sm"><span>{t("deliveryFee")}</span><span>{formatMoney(d.delivery_fee_paise)}</span></div>}
        <div className="flex justify-between"><span>{t("grandTotal")}</span><Price paise={d.grand_total_paise} /></div>
        {active && hasRiderBill && <div className="flex justify-between border-t pt-1 text-lg"><span className="font-bold">{t("cashToPay")}</span><Price paise={d.cash_to_collect_paise} /></div>}
      </div>
    </Section>
  );
}
