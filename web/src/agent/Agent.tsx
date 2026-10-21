import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, type CustomerLookup } from "../api";
import { Section } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";
import { OrdersList } from "../pages/Orders";

/** A helper-friendly random PIN: 4 digits, no repeated or running digits that are easy to guess. */
export function suggestPin(): string {
  for (;;) {
    const digits = Array.from(crypto.getRandomValues(new Uint8Array(4)), (b) => b % 10);
    const same = digits.every((d) => d === digits[0]);
    const run = digits.every((d, i) => i === 0 || d === digits[i - 1] + 1) || digits.every((d, i) => i === 0 || d === digits[i - 1] - 1);
    if (!same && !run) return digits.join("");
  }
}

export function AgentHome() {
  const { t, cart } = useApp();
  return (
    <div className="space-y-4">
      <Section title={t("agentHome")}>
        <div className="grid grid-cols-1 gap-3">
          <Link to="/" className="btn btn-primary !min-h-16 text-lg">🛒 {t("takeOrder")}{cart.length > 0 ? ` (${cart.length})` : ""}</Link>
          {cart.length > 0 && <Link to="/checkout" className="btn btn-ghost">{t("checkout")}</Link>}
          <Link to="/agent/register" className="btn btn-ghost !min-h-16 text-lg">🧑‍🌾 {t("registerVillager")}</Link>
        </div>
      </Section>
      <OrdersList base="/agent/orders" showPhone />
    </div>
  );
}

export function RegisterVillager() {
  const { t } = useApp();
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [pin, setPin] = useState(() => suggestPin());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ phone: string; name: string; pin: string } | null>(null);
  const lookup = useFetch<CustomerLookup>(phone.length === 10 ? `/staff/customers/${phone}` : null);

  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      await api("/staff/customers", { method: "POST", body: { phone, name: name || null, temp_pin: pin } });
      setDone({ phone, name, pin });
    } catch (err) { setError(err instanceof ApiError ? err.message : t("error")); } finally { setBusy(false); }
  }

  if (done) {
    return (
      <Section title={t("registered")}>
        <div className="card space-y-2 border-2 border-brand p-4 text-center">
          <p className="font-semibold">{done.name || done.phone}</p>
          <p>{t("phone")}: <b>{done.phone}</b></p>
          <p className="text-sm">{t("tempPin")}</p>
          <p className="text-5xl font-extrabold tracking-[0.3em] text-brand">{done.pin}</p>
          <p className="text-sm text-muted">{t("tellVillager")}</p>
        </div>
        <button className="btn btn-primary w-full" onClick={() => { setDone(null); setPhone(""); setName(""); setPin(suggestPin()); }}>{t("registerAnother")}</button>
      </Section>
    );
  }

  const found = lookup.data;
  return (
    <Section title={t("registerVillager")}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block space-y-1"><span className="font-semibold">{t("villagerPhone")}</span>
          <input className="input" inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} required value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} /></label>
        {found?.registered && <p className="rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-900">{t("alreadyRegistered")}{found.name ? `: ${found.name}` : ""}. {t("resetPinNote")}</p>}
        {lookup.error && phone.length === 10 && <p role="alert" className="text-sm font-semibold text-red-700">{lookup.error}</p>}
        <label className="block space-y-1"><span className="font-semibold">{t("yourName")}</span>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="block space-y-1"><span className="font-semibold">{t("tempPin")}</span>
          <div className="flex gap-2">
            <input className="input text-center text-2xl tracking-[0.4em]" inputMode="numeric" pattern="[0-9]{4,6}" maxLength={6} required value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
            <button type="button" className="btn btn-ghost" onClick={() => setPin(suggestPin())}>↻</button>
          </div></label>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 font-semibold text-red-700">{error}</p>}
        <button className="btn btn-primary w-full" disabled={busy || !!lookup.error}>{found?.registered ? t("resetPin") : t("registerVillager")}</button>
      </form>
    </Section>
  );
}
