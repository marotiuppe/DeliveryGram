import { useState } from "react";
import { api, ApiError, type Rate } from "../api";
import { ErrorBox, Section, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { bpsToPercent, percentToBps } from "./units";

function RateRow({ r, onSaved }: { r: Rate; onSaved: () => void }) {
  const { t, lang } = useApp();
  const [commission, setCommission] = useState(bpsToPercent(r.commission_bps));
  const [tax, setTax] = useState(bpsToPercent(r.tax_bps));
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save() {
    const c = percentToBps(commission), x = percentToBps(tax);
    if (c === null || x === null) { setError(`${t("commissionPct")} / ${t("taxPct")}`); return; }
    setBusy(true); setError(null); setSaved(false);
    try { await api(`/admin/store-types/${r.id}`, { method: "PATCH", body: { commission_bps: c, tax_bps: x } }); setSaved(true); onSaved(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); } finally { setBusy(false); }
  }

  return (
    <li className="card space-y-2 p-3">
      <p className="font-bold">{lang === "hi" && r.name_hi ? r.name_hi : r.name}</p>
      <div className="flex items-end gap-2">
        <label className="flex-1 space-y-1"><span className="text-sm font-semibold">{t("commissionPct")}</span>
          <input className="input" inputMode="decimal" value={commission} onChange={(e) => { setCommission(e.target.value); setSaved(false); }} /></label>
        <label className="flex-1 space-y-1"><span className="text-sm font-semibold">{t("taxPct")}</span>
          <input className="input" inputMode="decimal" value={tax} onChange={(e) => { setTax(e.target.value); setSaved(false); }} /></label>
        <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>{t("saveRates")}</button>
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      {saved && <p className="text-sm font-semibold text-green-700">{t("saved")}</p>}
    </li>
  );
}

export default function AdminRates() {
  const { t } = useApp();
  const res = useFetch<Rate[]>("/admin/store-types");
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  return (
    <Section title={t("adminRates")}>
      <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{t("ratesHelp")}</p>
      <ul className="space-y-2">{res.data.map((r) => <RateRow key={r.id} r={r} onSaved={res.reload} />)}</ul>
    </Section>
  );
}
