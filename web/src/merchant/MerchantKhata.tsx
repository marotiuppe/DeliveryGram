import { useState } from "react";
import { api, ApiError, type KhataAccount, type KhataEntry, type Store } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { StorePicker, WithStore } from "./common";
import { reminderMessage, rupeesToPaise, smsLink, whatsappLink } from "./reminder";

function History({ storeId, customerId }: { storeId: number; customerId: number }) {
  const { t } = useApp();
  const res = useFetch<KhataEntry[]>(`/merchant/stores/${storeId}/khata/${customerId}/entries`);
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  return (
    <ul className="divide-y text-sm">
      {res.data.map((e) => (
        <li key={e.id} className="flex justify-between py-1.5">
          <span>{new Date(e.created_at).toLocaleDateString()} · {e.kind === "SALE" ? t("sale") : t("payment")}{e.note ? ` · ${e.note}` : ""}</span>
          <span className={e.amount_paise > 0 ? "font-semibold text-red-700" : "font-semibold text-green-700"}>{e.amount_paise > 0 ? "+" : "−"}{formatMoney(Math.abs(e.amount_paise))}</span>
        </li>
      ))}
    </ul>
  );
}

function AccountCard({ a, store, onChanged }: { a: KhataAccount; store: Store; onChanged: () => void }) {
  const { t, lang } = useApp();
  const [mode, setMode] = useState<"payment" | "sale" | "history" | null>(null);
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const message = reminderMessage(lang, a.customer_name, store.name, a.balance_paise);

  async function record(kind: "PAYMENT" | "SALE") {
    const paise = rupeesToPaise(amount);
    if (!paise) { setError(t("amountRs")); return; }
    setBusy(true); setError(null);
    try {
      await api(`/merchant/stores/${store.id}/khata/${a.customer_id}/entries`, { method: "POST", body: { kind, amount_paise: paise, note: note || null } });
      setAmount(""); setNote(""); setMode(null); onChanged();
    } catch (e) { setError(e instanceof ApiError ? e.message : t("error")); } finally { setBusy(false); }
  }

  return (
    <li className="card space-y-2 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-bold">{a.customer_name ?? a.customer_phone}</p>
          {a.customer_name && <p className="text-sm text-muted">{a.customer_phone}</p>}
          <p className="text-xs text-muted">{t("creditLimit")} {formatMoney(a.credit_limit_paise)}{!a.enabled ? ` · ${t("paused")}` : ""}</p>
        </div>
        <div className="text-right"><p className="text-sm text-muted">{t("dues")}</p><Price paise={a.balance_paise} /></div>
      </div>

      {a.balance_paise > 0 && a.customer_phone && (
        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold">{t("sendReminder")}:</span>
          <a className="btn btn-ghost !min-h-10" href={whatsappLink(a.customer_phone, message)} target="_blank" rel="noreferrer">{t("whatsapp")}</a>
          <a className="btn btn-ghost !min-h-10" href={smsLink(a.customer_phone, message)}>{t("sms")}</a>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button className="btn btn-primary !min-h-10 flex-1" disabled={a.balance_paise === 0} onClick={() => setMode(mode === "payment" ? null : "payment")}>{t("receivedMoney")}</button>
        <button className="btn btn-ghost !min-h-10 flex-1" onClick={() => setMode(mode === "sale" ? null : "sale")}>{t("addSale")}</button>
        <button className="btn btn-ghost !min-h-10" onClick={() => setMode(mode === "history" ? null : "history")} aria-expanded={mode === "history"}>{t("history")}</button>
      </div>

      {(mode === "payment" || mode === "sale") && (
        <div className="space-y-2">
          <input className="input" inputMode="decimal" autoFocus placeholder={t("amountRs")} value={amount} onChange={(e) => setAmount(e.target.value)} />
          <input className="input" placeholder={t("note")} value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn btn-primary w-full" disabled={busy} onClick={() => void record(mode === "payment" ? "PAYMENT" : "SALE")}>{t("save")}</button>
        </div>
      )}
      {mode === "history" && <History storeId={store.id} customerId={a.customer_id} />}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
    </li>
  );
}

function GiveKhata({ storeId, onDone }: { storeId: number; onDone: () => void }) {
  const { t } = useApp();
  const [phone, setPhone] = useState("");
  const [limit, setLimit] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function save() {
    const paise = rupeesToPaise(limit);
    if (!/^[6-9]\d{9}$/.test(phone) || !paise) { setError(`${t("phone")} / ${t("limitRs")}`); return; }
    setError(null);
    try { await api(`/merchant/stores/${storeId}/khata/${phone}`, { method: "PUT", body: { credit_limit_paise: paise, enabled: true } }); setPhone(""); setLimit(""); onDone(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }
  return (
    <div className="card space-y-2 p-3">
      <p className="font-bold">{t("giveKhata")}</p>
      <input className="input" inputMode="numeric" maxLength={10} placeholder={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} />
      <div className="flex gap-2">
        <input className="input" inputMode="decimal" placeholder={t("limitRs")} value={limit} onChange={(e) => setLimit(e.target.value)} />
        <button className="btn btn-primary" onClick={() => void save()}>{t("save")}</button>
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
    </div>
  );
}

function KhataBody({ store, stores, pick }: { store: Store; stores: Store[]; pick: (id: number) => void }) {
  const { t } = useApp();
  const res = useFetch<KhataAccount[]>(`/merchant/stores/${store.id}/khata`);
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  const total = res.data.reduce((n, a) => n + a.balance_paise, 0);
  return (
    <section className="space-y-3">
      <StorePicker stores={stores} store={store} onPick={pick} />
      <div className="card flex items-center justify-between p-4"><span className="font-semibold">{t("totalDues")}</span><Price paise={total} /></div>
      <GiveKhata storeId={store.id} onDone={res.reload} />
      {res.data.length === 0 ? <p className="py-4 text-center text-muted">{t("noKhataCustomers")}</p> : (
        <ul className="space-y-3">{res.data.map((a) => <AccountCard key={`${a.customer_id}-${a.balance_paise}`} a={a} store={store} onChanged={res.reload} />)}</ul>
      )}
    </section>
  );
}

export default function MerchantKhata() {
  return <WithStore>{({ store, stores, pick }) => <KhataBody store={store} stores={stores} pick={pick} />}</WithStore>;
}
