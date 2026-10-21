import type { AdminStats, Order, SystemInfo } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Section, Spinner, StatusChip } from "../components";
import type { Key } from "../i18n";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

function Stat({ label, value, big }: { label: string; value: string | number; big?: boolean }) {
  return (
    <div className={`card p-3 ${big ? "border-l-4 border-l-brand" : ""}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`font-extrabold ${big ? "text-2xl text-brand-dark" : "text-xl"}`}>{value}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const { t } = useApp();
  const stats = useFetch<AdminStats>("/admin/stats", 30000);
  const orders = useFetch<Order[]>("/orders", 30000);
  const system = useFetch<SystemInfo>("/admin/system", 60000);
  if (stats.loading) return <Spinner />;
  if (stats.error || !stats.data) return <ErrorBox message={stats.error ?? "error"} onRetry={stats.reload} />;
  const s = stats.data;
  return (
    <Section title={t("adminHome")}>
      <div className="grid grid-cols-2 gap-3">
        <Stat label={t("ordersToday")} value={s.orders_today} big />
        <Stat label={t("deliveredSales")} value={formatMoney(s.delivered_sales_paise)} big />
        <Stat label={t("commissionToday")} value={formatMoney(s.commission_paise)} />
        <Stat label={t("deliveryFeesToday")} value={formatMoney(s.delivery_fees_paise)} />
        <Stat label={t("openTrips")} value={s.open_deliveries} />
        <Stat label={t("khataOutstanding")} value={formatMoney(s.khata_outstanding_paise)} />
        <Stat label={t("shopsCount")} value={s.shops} />
        <Stat label={t("ridersCount")} value={s.riders} />
        <Stat label={t("villagersCount")} value={s.villagers} />
      </div>
      {Object.keys(s.orders_by_status).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(s.orders_by_status).map(([k, n]) => <StatusChip key={k} text={`${t(`order${k}` as Key)}: ${n}`} tone={k === "DELIVERED" ? "green" : ["REJECTED", "CANCELLED", "FAILED"].includes(k) ? "red" : "amber"} />)}
        </div>
      )}
      {system.data && (
        <div className="card space-y-1 p-3 text-sm">
          <p className="text-base font-bold">{t("systemTitle")}</p>
          <p><span className="font-semibold">{t("systemDatabase")}:</span> {system.data.database}</p>
          <p><span className="font-semibold">{t("systemEmail")}:</span> {system.data.email_backend}</p>
          {system.data.last_email_error && <p role="alert" className="rounded-lg bg-red-50 p-2 font-semibold text-red-700">{t("systemLastError")}: {system.data.last_email_error}</p>}
          <p><span className="font-semibold">{t("systemKeepalive")}:</span> {system.data.keepalive_enabled ? `${t("systemOn")}${system.data.keepalive_last_ok === false ? ` - ${system.data.keepalive_last_error}` : ""}` : t("systemOff")}</p>
        </div>
      )}
      <h2 className="pt-2 text-lg font-bold">{t("recentOrders")}</h2>
      {orders.data?.slice(0, 10).map((o) => (
        <div key={o.id} className="card flex items-center justify-between gap-2 p-3">
          <div className="min-w-0"><p className="font-semibold">#{o.id} · {o.store_name}</p><p className="truncate text-sm text-muted">{o.items.map((i) => i.name).join(", ")}</p></div>
          <div className="text-right"><Price paise={o.total_paise} /><p className="text-xs text-muted">{t(`order${o.status}` as Key)}</p></div>
        </div>
      ))}
    </Section>
  );
}
