import { useState } from "react";
import { api, ApiError, type AdminStore, type Person, type StoreType, type Village } from "../api";
import { ErrorBox, Section, Spinner, StatusChip } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { bpsToPercent, percentToBps } from "./units";

function ShopCard({ s, onChanged }: { s: AdminStore; onChanged: () => void }) {
  const { t } = useApp();
  const [open, setOpen] = useState(false);
  const [rate, setRate] = useState(s.commission_bps === null ? "" : bpsToPercent(s.commission_bps));
  const [phone, setPhone] = useState(s.phone ?? "");
  const [licence, setLicence] = useState(s.drug_licence_no ?? "");
  const [fssai, setFssai] = useState(s.fssai_no ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  async function patch(body: Record<string, unknown>) {
    setBusy(true); setError(null); setSaved(false);
    try { await api(`/admin/stores/${s.id}`, { method: "PATCH", body }); setSaved(true); onChanged(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); } finally { setBusy(false); }
  }
  function save() {
    const bps = rate.trim() === "" ? null : percentToBps(rate);
    if (rate.trim() !== "" && bps === null) { setError(t("commissionPct")); return; }
    void patch({ commission_bps: bps, phone: phone || undefined, fssai_no: fssai || undefined, drug_licence_no: licence });
  }

  return (
    <li className="card space-y-2 p-3">
      <button className="flex w-full items-start justify-between gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>
          <span className="block font-bold">{s.name}</span>
          <span className="text-sm text-gray-600">{s.store_type_name} · {s.village_name}</span>
          <span className="block text-sm text-gray-600">{s.owner_phone ?? "—"} · {t("commissionPct")} {bpsToPercent(s.effective_commission_bps)}{s.commission_bps === null ? "" : " *"}</span>
        </span>
        {!s.active && <StatusChip text={t("disabled")} tone="red" />}
      </button>
      {open && (
        <div className="space-y-2 border-t pt-2">
          <label className="block space-y-1"><span className="text-sm font-semibold">{t("commissionPct")}</span>
            <input className="input" inputMode="decimal" placeholder={bpsToPercent(s.effective_commission_bps)} value={rate} onChange={(e) => setRate(e.target.value)} />
            <span className="text-xs text-gray-600">{t("useTypeRate")}</span></label>
          <input className="input" inputMode="numeric" maxLength={10} placeholder={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} />
          <input className="input" placeholder={t("fssai")} value={fssai} onChange={(e) => setFssai(e.target.value)} />
          <input className="input" placeholder={t("drugLicence")} value={licence} onChange={(e) => setLicence(e.target.value)} />
          {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
          {saved && <p className="text-sm font-semibold text-green-700">{t("saved")}</p>}
          <div className="flex gap-2">
            <button className="btn btn-primary flex-1" disabled={busy} onClick={save}>{t("save")}</button>
            <button className={`btn flex-1 ${s.active ? "btn-ghost" : "btn-primary"}`} disabled={busy} onClick={() => void patch({ active: !s.active })}>{s.active ? t("disable") : t("enable")}</button>
          </div>
        </div>
      )}
    </li>
  );
}

function AddShop({ onDone }: { onDone: () => void }) {
  const { t, lang } = useApp();
  const owners = useFetch<Person[]>("/admin/users?role=merchant");
  const types = useFetch<StoreType[]>("/store-types");
  const villages = useFetch<Village[]>("/villages");
  const [ownerId, setOwnerId] = useState("");
  const [typeCode, setTypeCode] = useState("");
  const [villageId, setVillageId] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [fssai, setFssai] = useState("");
  const [licence, setLicence] = useState("");
  const [error, setError] = useState<string | null>(null);
  const type = types.data?.find((x) => x.code === typeCode);

  async function save() {
    setError(null);
    try {
      await api("/admin/stores", { method: "POST", body: {
        owner_id: Number(ownerId), store_type_code: typeCode, village_id: Number(villageId), name, phone: phone || null,
        fssai_no: fssai || null, drug_licence_no: licence || null } });
      setName(""); setPhone(""); setFssai(""); setLicence("");
      onDone();
    } catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }
  if (owners.loading || types.loading || villages.loading) return <Spinner />;
  if (!owners.data?.length) return <p className="card p-3 text-center">{t("needOwner")}</p>;
  return (
    <div className="card space-y-2 p-3">
      <p className="font-bold">{t("addShop")}</p>
      <select className="input" aria-label={t("owner")} value={ownerId} onChange={(e) => setOwnerId(e.target.value)}>
        <option value="">{t("owner")}</option>
        {owners.data.map((o) => <option key={o.id} value={o.id}>{o.name ?? o.phone} {o.phone ? `(${o.phone})` : ""}</option>)}
      </select>
      <select className="input" aria-label={t("shopType")} value={typeCode} onChange={(e) => setTypeCode(e.target.value)}>
        <option value="">{t("shopType")}</option>
        {types.data?.map((x) => <option key={x.code} value={x.code}>{lang === "hi" && x.name_hi ? x.name_hi : x.name}</option>)}
      </select>
      <select className="input" aria-label={t("village")} value={villageId} onChange={(e) => setVillageId(e.target.value)}>
        <option value="">{t("village")}</option>
        {villages.data?.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
      </select>
      <input className="input" placeholder={t("shopName")} value={name} onChange={(e) => setName(e.target.value)} />
      <input className="input" inputMode="numeric" maxLength={10} placeholder={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} />
      <input className="input" placeholder={t("fssai")} value={fssai} onChange={(e) => setFssai(e.target.value)} />
      {type?.needs_prescription && <input className="input" placeholder={`${t("drugLicence")} *`} value={licence} onChange={(e) => setLicence(e.target.value)} />}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      <button className="btn btn-primary w-full" disabled={!ownerId || !typeCode || !villageId || name.trim().length < 2} onClick={() => void save()}>{t("addShop")}</button>
    </div>
  );
}

export default function AdminShops() {
  const { t } = useApp();
  const res = useFetch<AdminStore[]>("/admin/stores");
  const [adding, setAdding] = useState(false);
  return (
    <Section title={t("adminShops")}>
      <button className={`btn w-full ${adding ? "btn-primary" : "btn-ghost"}`} onClick={() => setAdding(!adding)}>{t("addShop")}</button>
      {adding && <AddShop onDone={res.reload} />}
      {res.loading ? <Spinner /> : res.error || !res.data ? <ErrorBox message={res.error ?? "error"} onRetry={res.reload} /> : res.data.length === 0 ? <p className="py-6 text-center text-gray-500">{t("noShopsAdmin")}</p> : (
        <ul className="space-y-2">{res.data.map((s) => <ShopCard key={s.id} s={s} onChanged={res.reload} />)}</ul>
      )}
    </Section>
  );
}
