import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import type { Delivery } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Section, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

function beep() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    osc.frequency.value = 660;
    osc.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
  } catch { /* audio blocked until the first tap */ }
}

const sameDay = (iso: string) => new Date(iso).toDateString() === new Date().toDateString();

export function JobCard({ d }: { d: Delivery }) {
  const { t } = useApp();
  const live = d.orders.filter((o) => !["REJECTED", "CANCELLED"].includes(o.status) && o.fulfillment === "delivery");
  return (
    <Link to={`/rider/${d.id}`} className="card block space-y-1 p-3">
      <div className="flex items-center justify-between">
        <span className="font-bold">{t("tripWord")} #{d.id}</span>
        {d.cash_to_collect_paise > 0 ? <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-900">{formatMoney(d.cash_to_collect_paise)}</span> : null}
      </div>
      <p className="text-sm text-muted">🏪 {t("collectFrom")}: {live.map((o) => o.store_name).join(", ")}</p>
      <p className="text-sm text-muted">📍 {t("deliverTo")}: {d.ward_number ? `${t("ward")} ${d.ward_number}, ` : ""}{d.landmark}</p>
    </Link>
  );
}

export default function RiderJobs() {
  const { t, me } = useApp();
  const res = useFetch<Delivery[]>("/deliveries", 10000);
  const seen = useRef<number | null>(null);
  const all = res.data ?? [];
  const ready = all.filter((d) => d.status === "OPEN" && d.rider_id === null);
  const onTheWay = all.filter((d) => d.status === "OUT_FOR_DELIVERY" && d.rider_id === me?.id);
  const done = all.filter((d) => ["DELIVERED", "FAILED"].includes(d.status) && d.rider_id === me?.id && sameDay(d.created_at));
  const cash = done.filter((d) => d.status === "DELIVERED").reduce((n, d) => n + d.cash_to_collect_paise, 0);

  useEffect(() => {
    if (res.loading || !res.data) return;
    if (seen.current !== null && ready.length > seen.current) beep();
    seen.current = ready.length;
    document.title = ready.length ? `(${ready.length}) DeliveryGram` : "DeliveryGram";
  }, [res.data, res.loading, ready.length]);

  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;

  const group = (title: string, list: Delivery[]) => list.length === 0 ? null : (
    <section className="space-y-2"><h2 className="text-lg font-bold">{title} ({list.length})</h2>{list.map((d) => <JobCard key={d.id} d={d} />)}</section>
  );
  return (
    <Section title={t("riderJobs")}>
      <div className="card flex items-center justify-between border-amber-300 bg-amber-50 p-4 text-lg"><span className="font-bold">💰 {t("cashWithMe")}</span><Price paise={cash} /></div>
      {group(t("myTrips"), onTheWay)}
      {group(t("readyForPickup"), ready)}
      {ready.length === 0 && onTheWay.length === 0 && <p className="card py-8 text-center text-muted"><span aria-hidden className="block text-4xl">🛵</span>{t("noJobs")}</p>}
      {group(t("doneToday"), done)}
    </Section>
  );
}
