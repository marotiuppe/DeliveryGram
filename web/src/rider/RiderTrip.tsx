import { useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError, type Delivery } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Section, Spinner, StatusChip } from "../components";
import type { Key } from "../i18n";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

export default function RiderTrip() {
  const { id } = useParams();
  const { t, me } = useApp();
  const res = useFetch<Delivery>(`/deliveries/${id}`, 10000);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmFail, setConfirmFail] = useState(false);

  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  const d = res.data;
  const mine = d.rider_id === me?.id;
  const open = d.status === "OPEN" && d.rider_id === null;
  const onTheWay = d.status === "OUT_FOR_DELIVERY" && mine;
  const carried = d.orders.filter((o) => o.fulfillment === "delivery" && !["REJECTED", "CANCELLED"].includes(o.status));
  const pickupOnly = d.orders.filter((o) => o.fulfillment === "pickup" && !["REJECTED", "CANCELLED"].includes(o.status));

  async function act(path: string, body?: unknown) {
    setBusy(true); setError(null);
    try { await api(`/deliveries/${d.id}/${path}`, { method: "POST", body: body ?? {} }); setConfirmFail(false); await res.reload(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); } finally { setBusy(false); }
  }

  const needsCode = d.delivery_code_required;
  return (
    <Section title={`${t("tripWord")} #${d.id}`}>
      <StatusChip text={t(`status${d.status}` as Key)} tone={d.status === "DELIVERED" ? "green" : d.status === "FAILED" ? "red" : "amber"} />

      <div className="space-y-2">
        <h2 className="text-lg font-bold">{t("collectFrom")}</h2>
        {carried.map((o) => (
          <div key={o.id} className="card space-y-1 p-3">
            <div className="flex items-center justify-between">
              <p className="font-bold text-brand">{o.store_name}</p>
              {o.store_phone && <a className="text-sm font-semibold text-brand underline" href={`tel:${o.store_phone}`}>{t("callShop")}</a>}
            </div>
            <ul className="text-sm">{o.items.map((i) => <li key={i.store_item_id}>{i.name} × {i.quantity}</li>)}</ul>
            <p className="text-xs text-muted">{t("bill")} #{o.id} · {formatMoney(o.total_paise)}{o.payment_method === "khata" ? ` · ${t("onKhata")}` : o.payment_method === "upi" ? " · UPI" : ""}</p>
          </div>
        ))}
        {pickupOnly.length > 0 && <p className="text-xs text-muted">{pickupOnly.map((o) => o.store_name).join(", ")}: {t("payAtShop")}</p>}
      </div>

      <div className="card space-y-1 p-3">
        <h2 className="text-lg font-bold">{t("deliverTo")}</h2>
        <p>{d.village_name}{d.ward_number ? `, ${t("ward")} ${d.ward_number}` : ""}</p>
        <p className="font-semibold">{d.landmark}</p>
        {d.address_details && <p className="text-sm text-gray-700">{d.address_details}</p>}
        <a className="inline-block font-semibold text-brand underline" href={`tel:${d.contact_phone}`}>{t("callCustomer")}: {d.contact_phone}</a>
      </div>

      <div className="card border-2 border-amber-300 p-4 text-center">
        <p className="font-semibold">{t("collectCash")}</p>
        {d.cash_to_collect_paise > 0 ? <p className="text-4xl font-extrabold"><Price paise={d.cash_to_collect_paise} /></p> : <p className="text-sm text-muted">{t("noCashBills")}</p>}
      </div>

      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 font-semibold text-red-700">{error}</p>}

      {open && <button className="btn btn-primary w-full" disabled={busy} onClick={() => void act("claim")}>{t("takeDelivery")}</button>}

      {onTheWay && (
        <div className="space-y-3">
          {needsCode && (
            <label className="block space-y-1"><span className="font-semibold">{t("enterCode")}</span>
              <input className="input text-center text-3xl tracking-[0.5em]" inputMode="numeric" maxLength={4} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
              <span className="text-sm text-muted">{t("codeNeeded")}</span></label>
          )}
          <button className="btn btn-primary w-full" disabled={busy || (needsCode && code.length !== 4)} onClick={() => void act("complete", { delivery_code: needsCode ? code : null })}>{t("delivered")}</button>
          {!confirmFail ? (
            <button className="btn btn-ghost w-full" onClick={() => setConfirmFail(true)}>{t("cantDeliver")}</button>
          ) : (
            <div className="card space-y-2 p-3"><p className="font-semibold">{t("sureFail")}</p>
              <div className="flex gap-2"><button className="btn btn-ghost flex-1" onClick={() => setConfirmFail(false)}>{t("no")}</button><button className="btn flex-1 bg-red-600 text-white" disabled={busy} onClick={() => void act("fail")}>{t("yes")}</button></div></div>
          )}
        </div>
      )}
    </Section>
  );
}
