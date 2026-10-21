import { useEffect, useRef, useState } from "react";
import { api, ApiError, type Order, type Store } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Spinner, StatusChip } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { StorePicker, WithStore } from "./common";

const NEW = ["PLACED", "PENDING_PRESCRIPTION_REVIEW"];

/** A short beep so a busy shopkeeper notices a new order. Browsers may block audio before the first tap; that is fine. */
function beep() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    osc.frequency.value = 880;
    osc.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
  } catch { /* no audio available */ }
}

function OrderCard({ o, onChanged }: { o: Order; onChanged: () => void }) {
  const { t } = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [askCode, setAskCode] = useState(false);
  const [code, setCode] = useState("");

  async function move(status: string, deliveryCode?: string) {
    setBusy(true); setError(null);
    try {
      await api(`/orders/${o.id}/status`, { method: "POST", body: { status, delivery_code: deliveryCode || null } });
      setAskCode(false); setCode("");
      onChanged();
    } catch (e) {
      if (e instanceof ApiError && e.status === 422 && status === "DELIVERED") setAskCode(true);
      setError(e instanceof ApiError ? e.message : t("error"));
    } finally { setBusy(false); }
  }

  const pay = o.payment_method === "khata" ? t("onKhata") : o.payment_method === "upi" ? t("upiBill") : t("cashBill");
  return (
    <div className="card space-y-2 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-bold">{t("bill")} #{o.id}</span>
        <span className="flex gap-1">
          <StatusChip text={o.fulfillment === "pickup" ? t("forPickup") : t("forDelivery")} tone="gray" />
          <StatusChip text={pay} tone={o.payment_method === "khata" ? "amber" : "gray"} />
        </span>
      </div>
      <ul className="text-sm">{o.items.map((i) => <li key={i.store_item_id} className="flex justify-between"><span>{i.name} × {i.quantity}</span><span>{formatMoney(i.unit_price_paise * i.quantity)}</span></li>)}</ul>
      <div className="flex justify-between border-t pt-1"><span>{t("total")}</span><Price paise={o.total_paise} /></div>
      <p className="text-sm text-muted">{o.landmark}</p>
      <a className="inline-block text-sm font-semibold text-brand underline" href={`tel:${o.contact_phone}`}>{t("callCustomer")}: {o.contact_phone}</a>
      {o.prescription_ref && <p className="rounded-lg bg-red-50 p-2 text-sm"><b>{t("prescription")}:</b> {o.prescription_ref}</p>}

      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      {askCode && (
        <input className="input text-center text-xl tracking-[0.4em]" inputMode="numeric" maxLength={4} placeholder={t("codeFromCustomer")} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
      )}
      <div className="flex gap-2">
        {o.status === "PENDING_PRESCRIPTION_REVIEW" && <button className="btn btn-primary flex-1" disabled={busy} onClick={() => void move("PLACED")}>{t("verifyRx")}</button>}
        {o.status === "PLACED" && <button className="btn btn-primary flex-1" disabled={busy} onClick={() => void move("ACCEPTED")}>{t("accept")}</button>}
        {NEW.includes(o.status) && <button className="btn btn-ghost flex-1" disabled={busy} onClick={() => void move("REJECTED")}>{t("reject")}</button>}
        {o.status === "ACCEPTED" && <button className="btn btn-primary flex-1" disabled={busy} onClick={() => void move("READY")}>{t("markReady")}</button>}
        {o.status === "READY" && o.fulfillment === "pickup" && (
          <button className="btn btn-primary flex-1" disabled={busy || (askCode && code.length !== 4)} onClick={() => void move("DELIVERED", code)}>{t("handOver")}</button>
        )}
      </div>
    </div>
  );
}

function Column({ title, orders, reload }: { title: string; orders: Order[]; reload: () => void }) {
  if (orders.length === 0) return null;
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-bold">{title} ({orders.length})</h2>
      {orders.map((o) => <OrderCard key={o.id} o={o} onChanged={reload} />)}
    </section>
  );
}

function Board({ store, stores, pick }: { store: Store; stores: Store[]; pick: (id: number) => void }) {
  const { t } = useApp();
  const res = useFetch<Order[]>("/orders", 10000);
  const [isOpen, setIsOpen] = useState(store.is_open);
  const seen = useRef<number | null>(null);
  const mine = (res.data ?? []).filter((o) => o.store_id === store.id);
  const fresh = mine.filter((o) => NEW.includes(o.status));

  useEffect(() => { setIsOpen(store.is_open); }, [store]);
  useEffect(() => {
    if (res.loading || !res.data) return;
    if (seen.current !== null && fresh.length > seen.current) beep();
    seen.current = fresh.length;
    document.title = fresh.length ? `(${fresh.length}) DeliveryGram` : "DeliveryGram";
  }, [res.data, res.loading, fresh.length]);

  async function toggleOpen() {
    const next = !isOpen;
    setIsOpen(next);
    try { await api(`/merchant/stores/${store.id}/open`, { method: "PATCH", body: { is_open: next } }); } catch { setIsOpen(!next); }
  }

  return (
    <section className="space-y-4">
      <StorePicker stores={stores} store={store} onPick={pick} />
      <button className={`btn w-full ${isOpen ? "btn-primary" : "btn-ghost"}`} onClick={() => void toggleOpen()}>{isOpen ? t("shopOpen") : t("shopClosed")}</button>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : (
        <>
          <Column title={t("newOrders")} orders={fresh} reload={res.reload} />
          <Column title={t("preparing")} orders={mine.filter((o) => o.status === "ACCEPTED")} reload={res.reload} />
          <Column title={t("readyOrders")} orders={mine.filter((o) => o.status === "READY")} reload={res.reload} />
          {!mine.some((o) => ["PLACED", "PENDING_PRESCRIPTION_REVIEW", "ACCEPTED", "READY"].includes(o.status)) && <p className="py-8 text-center text-muted">{t("noActiveOrders")}</p>}
        </>
      )}
    </section>
  );
}

export default function MerchantOrders() {
  return <WithStore>{({ store, stores, pick }) => <Board store={store} stores={stores} pick={pick} />}</WithStore>;
}
