import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError, type CustomerLookup, type Delivery, type KhataAccount, type Village } from "../api";
import { cartSubtotal, formatMoney, groupByShop } from "../cart";
import { ErrorBox, Price, Section, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

type Pay = "cod" | "upi" | "khata";
type Ful = "delivery" | "pickup";

/** One stable key per cart contents, so a retry after a dropped connection can never create a second order. */
function idempotencyKey(signature: string): string {
  const k = "dg_idem:" + signature;
  try {
    const existing = sessionStorage.getItem(k);
    if (existing) return existing;
    const fresh = crypto.randomUUID();
    sessionStorage.setItem(k, fresh);
    return fresh;
  } catch {
    return crypto.randomUUID();
  }
}

export default function Checkout() {
  const { t, cart, clearCart, me, villageId, online } = useApp();
  const nav = useNavigate();
  const villages = useFetch<Village[]>("/villages");
  const khata = useFetch<KhataAccount[]>(me?.role === "customer" ? "/khata" : null);
  const groups = useMemo(() => groupByShop(cart), [cart]);
  const isStaff = me?.role === "agent"; // a village helper ordering on behalf of a villager
  const [phone, setPhone] = useState(isStaff ? "" : me?.phone ?? "");
  const [name, setName] = useState(isStaff ? "" : me?.name ?? "");
  const [via, setVia] = useState<"phone" | "whatsapp">("phone");
  const lookup = useFetch<CustomerLookup>(isStaff && phone.length === 10 ? `/staff/customers/${phone}` : null);
  useEffect(() => { if (isStaff && lookup.data?.name && !name) setName(lookup.data.name); }, [isStaff, lookup.data, name]);
  const [wardId, setWardId] = useState<number | null>(null);
  const [landmark, setLandmark] = useState("");
  const [details, setDetails] = useState("");
  const [pay, setPay] = useState<Record<number, Pay>>({});
  const [ful, setFul] = useState<Record<number, Ful>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (cart.length === 0) return <Section title={t("checkoutTitle")}><Link className="btn btn-primary" to="/">{t("browseShops")}</Link></Section>;
  if (villages.loading) return <Spinner />;
  const village = villages.data?.find((v) => v.id === villageId);
  if (!village) return <ErrorBox message={villages.error ?? t("chooseVillage")} onRetry={villages.reload} />;

  const fulOf = (storeId: number): Ful => ful[storeId] ?? "delivery";
  const anyDelivery = groups.some((g) => fulOf(g.storeId) === "delivery");
  const fee = anyDelivery ? village.delivery_fee_paise : 0; // pickup-only carts pay no delivery fee
  const subtotal = cartSubtotal(cart);
  const khataFor = (storeId: number) => khata.data?.find((a) => a.store_id === storeId && a.enabled);
  const method = (storeId: number): Pay => pay[storeId] ?? "cod";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!online) { setError(t("offlineCheckout")); return; }
    setBusy(true);
    const signature = cart.map((l) => `${l.storeItemId}x${l.qty}`).join(",") + `|${landmark}|${phone}|${groups.map((g) => method(g.storeId) + fulOf(g.storeId)).join("")}`;
    try {
      const d = await api<Delivery>("/checkout", {
        method: "POST",
        body: {
          idempotency_key: idempotencyKey(signature), customer_phone: phone, customer_name: name || null, source: isStaff ? via : "app",
          village_id: village!.id, ward_id: wardId, landmark, address_details: details || null,
          shops: groups.map((g) => ({
            store_id: g.storeId, payment_method: method(g.storeId), fulfillment: fulOf(g.storeId),
            items: g.lines.map((l) => ({ store_item_id: l.storeItemId, quantity: l.qty })),
          })),
        },
      });
      clearCart();
      nav(isStaff ? `/agent/orders/${d.id}` : `/orders/${d.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? (err.message === "offline" ? t("offlineCheckout") : err.message) : t("error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section title={t("checkoutTitle")}>
      <form onSubmit={submit} className="space-y-4">
        {isStaff && (
          <div className="flex gap-2">
            {(["phone", "whatsapp"] as const).map((v) => (
              <button key={v} type="button" onClick={() => setVia(v)} className={`flex-1 rounded-xl px-3 py-3 font-semibold ${via === v ? "bg-brand text-white" : "border border-gray-300 bg-white"}`}>
                {v === "phone" ? t("viaPhone") : t("viaWhatsapp")}
              </button>
            ))}
          </div>
        )}
        <label className="block space-y-1"><span className="font-semibold">{isStaff ? t("customerPhoneStaff") : t("yourPhone")}</span>
          <input className="input" inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} required value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} /></label>
        {isStaff && phone.length === 10 && (lookup.error
          ? <p role="alert" className="text-sm font-semibold text-red-700">{lookup.error}</p>
          : lookup.data && <p className="text-sm font-semibold text-brand">{lookup.data.registered ? `${t("knownVillager")}${lookup.data.name ? `: ${lookup.data.name}` : ""}` : t("newVillager")}</p>)}
        <label className="block space-y-1"><span className="font-semibold">{t("yourName")}</span>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label>

        <div className="card space-y-3 p-3">
          <p className="font-bold">{village.name}</p>
          <label className="block space-y-1"><span className="font-semibold">{t("ward")}</span>
            <select className="input" value={wardId ?? ""} onChange={(e) => setWardId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">—</option>
              {village.wards.map((w) => <option key={w.id} value={w.id}>{t("ward")} {w.number}{w.name ? ` - ${w.name}` : ""}</option>)}
            </select></label>
          <label className="block space-y-1"><span className="font-semibold">{t("landmark")}</span>
            <input className="input" required minLength={2} value={landmark} onChange={(e) => setLandmark(e.target.value)} /></label>
          <label className="block space-y-1"><span className="font-semibold">{t("addressDetails")}</span>
            <input className="input" value={details} onChange={(e) => setDetails(e.target.value)} /></label>
        </div>

        {groups.map((g) => {
          const acct = khataFor(g.storeId);
          const options: [Pay, string][] = [["cod", t("payCash")], ["upi", t("payUpi")], ...(acct || isStaff ? [["khata", t("payKhata")] as [Pay, string]] : [])]; // staff: the server checks the villager's khata
          return (
            <fieldset key={g.storeId} className="card space-y-2 p-3">
              <legend className="px-1 font-bold text-brand">{g.storeName} — {t("bill")} {formatMoney(g.subtotalPaise)}</legend>
              {([["delivery", t("deliveryHome")], ["pickup", t("pickupShop")]] as [Ful, string][]).map(([val, label]) => (
                <label key={val} className="flex min-h-12 items-center gap-3 rounded-xl border border-gray-300 px-3">
                  <input type="radio" name={`ful-${g.storeId}`} checked={fulOf(g.storeId) === val} onChange={() => setFul((f) => ({ ...f, [g.storeId]: val }))} className="h-5 w-5" />
                  <span>{label}</span>
                </label>
              ))}
              {fulOf(g.storeId) === "pickup" && <p className="text-sm text-gray-600">{t("pickupNote")}</p>}
              <p className="pt-1 text-sm text-gray-600">{t("payHow")}</p>
              {options.map(([val, label]) => (
                <label key={val} className="flex min-h-12 items-center gap-3 rounded-xl border border-gray-300 px-3">
                  <input type="radio" name={`pay-${g.storeId}`} checked={method(g.storeId) === val} onChange={() => setPay((p) => ({ ...p, [g.storeId]: val }))} className="h-5 w-5" />
                  <span>{label}{val === "khata" && acct ? ` (${t("youOwe")} ${formatMoney(acct.balance_paise)} / ${t("creditLimit")} ${formatMoney(acct.credit_limit_paise)})` : ""}</span>
                </label>
              ))}
            </fieldset>
          );
        })}

        <div className="card space-y-1 p-4">
          <div className="flex justify-between"><span>{t("total")}</span><Price paise={subtotal} /></div>
          {anyDelivery && <div className="flex justify-between text-sm text-gray-600"><span>{t("deliveryFee")}</span><span>{formatMoney(fee)}</span></div>}
          <div className="flex justify-between border-t pt-2 text-lg"><span className="font-bold">{t("grandTotal")}</span><Price paise={subtotal + fee} /></div>
        </div>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 font-semibold text-red-700">{error}</p>}
        <button className="btn btn-primary w-full" disabled={busy || !online || (isStaff && !!lookup.error)}>{busy ? t("placing") : t("placeOrder")}</button>
        {!online && <p className="text-center text-sm text-amber-800">{t("offlineCheckout")}</p>}
      </form>
    </Section>
  );
}
