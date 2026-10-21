import { useState } from "react";
import { api, ApiError, type Village } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Section, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { feeToPaise } from "./units";

function VillageCard({ v, onChanged }: { v: Village; onChanged: () => void }) {
  const { t } = useApp();
  const [open, setOpen] = useState(false);
  const [fee, setFee] = useState("");
  const [num, setNum] = useState("");
  const [wname, setWname] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setError(null);
    try { await fn(); onChanged(); } catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }
  function saveFee() {
    const paise = feeToPaise(fee);
    if (paise === undefined) { setError(t("deliveryFeeRs")); return; }
    void run(() => api(`/admin/villages/${v.id}`, { method: "PATCH", body: { delivery_fee_paise: paise } }));
  }
  function addWard() {
    const n = Number(num);
    if (!Number.isInteger(n) || n < 1) { setError(t("wardNumber")); return; }
    void run(async () => { await api(`/admin/villages/${v.id}/wards`, { method: "POST", body: { number: n, name: wname || null } }); setNum(""); setWname(""); });
  }

  return (
    <li className="card space-y-2 p-3">
      <button className="flex w-full items-start justify-between text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span><span className="block font-bold">{v.name}</span><span className="text-sm text-muted">{[v.district, v.state].filter(Boolean).join(", ")}</span></span>
        <span className="text-right text-sm"><span className="block">{t("deliveryFeeRs")}: {formatMoney(v.delivery_fee_paise)}</span><span className="text-muted">{v.wards.length} {t("wardsWord")}</span></span>
      </button>
      {open && (
        <div className="space-y-3 border-t pt-2">
          <div className="flex flex-wrap gap-1">{v.wards.map((w) => <span key={w.id} className="rounded-full bg-gray-100 px-3 py-1 text-sm">{w.number}{w.name ? ` ${w.name}` : ""}</span>)}</div>
          <div className="flex gap-2">
            <input className="input" inputMode="decimal" placeholder={`${t("deliveryFeeRs")} (${t("feeBlankDefault")})`} value={fee} onChange={(e) => setFee(e.target.value)} />
            <button className="btn btn-primary" onClick={saveFee}>{t("save")}</button>
          </div>
          <div className="flex gap-2">
            <input className="input !w-28" inputMode="numeric" placeholder={t("wardNumber")} value={num} onChange={(e) => setNum(e.target.value.replace(/\D/g, ""))} />
            <input className="input" placeholder={t("wardName")} value={wname} onChange={(e) => setWname(e.target.value)} />
            <button className="btn btn-primary" onClick={addWard}>{t("addWard")}</button>
          </div>
          {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
        </div>
      )}
    </li>
  );
}

function AddVillage({ onDone }: { onDone: () => void }) {
  const { t } = useApp();
  const [name, setName] = useState("");
  const [district, setDistrict] = useState("");
  const [state, setState] = useState("");
  const [fee, setFee] = useState("");
  const [wards, setWards] = useState("0");
  const [error, setError] = useState<string | null>(null);

  async function save() {
    const paise = feeToPaise(fee);
    if (paise === undefined) { setError(t("deliveryFeeRs")); return; }
    setError(null);
    try {
      await api("/admin/villages", { method: "POST", body: { name, district: district || null, state: state || null, delivery_fee_paise: paise, ward_count: Number(wards) || 0 } });
      setName(""); setDistrict(""); setState(""); setFee(""); setWards("0");
      onDone();
    } catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }
  return (
    <div className="card space-y-2 p-3">
      <p className="font-bold">{t("addVillage")}</p>
      <input className="input" placeholder={t("village")} value={name} onChange={(e) => setName(e.target.value)} />
      <div className="flex gap-2">
        <input className="input" placeholder={t("district")} value={district} onChange={(e) => setDistrict(e.target.value)} />
        <input className="input" placeholder={t("state")} value={state} onChange={(e) => setState(e.target.value)} />
      </div>
      <div className="flex gap-2">
        <input className="input" inputMode="decimal" placeholder={`${t("deliveryFeeRs")} (${t("feeBlankDefault")})`} value={fee} onChange={(e) => setFee(e.target.value)} />
        <input className="input !w-32" inputMode="numeric" aria-label={t("wardCount")} placeholder={t("wardCount")} value={wards} onChange={(e) => setWards(e.target.value.replace(/\D/g, ""))} />
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      <button className="btn btn-primary w-full" disabled={name.trim().length < 2} onClick={() => void save()}>{t("addVillage")}</button>
    </div>
  );
}

export default function AdminVillages() {
  const { t } = useApp();
  const res = useFetch<Village[]>("/villages");
  const [adding, setAdding] = useState(false);
  return (
    <Section title={t("adminVillages")}>
      <button className={`btn w-full ${adding ? "btn-primary" : "btn-ghost"}`} onClick={() => setAdding(!adding)}>{t("addVillage")}</button>
      {adding && <AddVillage onDone={res.reload} />}
      {res.loading ? <Spinner /> : res.error || !res.data ? <ErrorBox message={res.error ?? "error"} onRetry={res.reload} /> : (
        <ul className="space-y-2">{res.data.map((v) => <VillageCard key={v.id} v={v} onChanged={res.reload} />)}</ul>
      )}
    </Section>
  );
}
