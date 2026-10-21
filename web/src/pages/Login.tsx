import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError, type TokenOut } from "../api";
import { Section } from "../components";
import { useApp } from "../state";

// Roles that have their own home screen; they land there after login instead of the shop list.
const STAFF = ["merchant", "rider", "agent", "admin"];

export default function Login() {
  const { t, me, onLogin } = useApp();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") && params.get("next")!.startsWith("/") ? params.get("next")! : "/";
  const [mode, setMode] = useState<"pin" | "email">("pin");
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (me && !me.pin_must_change) return <Navigate to={next === "/" && STAFF.includes(me.role) ? `/${me.role}` : next} replace />;

  async function finish(tok: TokenOut) {
    const m = await onLogin(tok.access_token);
    const dest = next === "/" && STAFF.includes(tok.role) ? `/${tok.role}` : next;
    nav(m?.pin_must_change || tok.pin_must_change ? `/change-pin?next=${encodeURIComponent(dest)}` : dest, { replace: true });
  }

  async function run(fn: () => Promise<void>) {
    setBusy(true); setError(null);
    try { await fn(); } catch (e) { setError(e instanceof ApiError ? (e.message === "offline" ? t("offline") : e.message) : t("error")); } finally { setBusy(false); }
  }

  const pinLogin = (e: FormEvent) => { e.preventDefault(); void run(async () => finish(await api<TokenOut>("/auth/pin/login", { method: "POST", body: { phone, pin } }))); };
  const sendCode = (e: FormEvent) => { e.preventDefault(); void run(async () => { await api("/auth/otp/request", { method: "POST", body: { email } }); setSent(true); }); };
  const verify = (e: FormEvent) => { e.preventDefault(); void run(async () => finish(await api<TokenOut>("/auth/otp/verify", { method: "POST", body: { email, code } }))); };

  const tab = (m: "pin" | "email", label: string) => (
    <button type="button" onClick={() => { setMode(m); setError(null); }} className={`flex-1 rounded-xl px-3 py-3 font-semibold ${mode === m ? "bg-brand text-white" : "bg-white border border-gray-300"}`}>{label}</button>
  );

  return (
    <Section title={t("login")}>
      <div className="flex gap-2">{tab("pin", t("loginPin"))}{tab("email", t("loginEmail"))}</div>
      {mode === "pin" ? (
        <form onSubmit={pinLogin} className="space-y-3">
          <label className="block space-y-1"><span className="font-semibold">{t("phone")}</span>
            <input className="input" inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} required value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} autoComplete="tel" /></label>
          <label className="block space-y-1"><span className="font-semibold">{t("pin")}</span>
            <input className="input" type="password" inputMode="numeric" pattern="[0-9]{4,6}" maxLength={6} required value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoComplete="current-password" /></label>
          <button className="btn btn-primary w-full" disabled={busy}>{t("login")}</button>
          <p className="text-sm text-gray-600">{t("pinHelp")}</p>
        </form>
      ) : !sent ? (
        <form onSubmit={sendCode} className="space-y-3">
          <label className="block space-y-1"><span className="font-semibold">{t("email")}</span>
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></label>
          <button className="btn btn-primary w-full" disabled={busy}>{t("sendCode")}</button>
        </form>
      ) : (
        <form onSubmit={verify} className="space-y-3">
          <p className="rounded-xl bg-brand-soft p-3">{t("codeSent")}</p>
          <label className="block space-y-1"><span className="font-semibold">{t("code")}</span>
            <input className="input text-center text-2xl tracking-[0.4em]" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} autoComplete="one-time-code" /></label>
          <button className="btn btn-primary w-full" disabled={busy}>{t("verify")}</button>
        </form>
      )}
      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 font-semibold text-red-700">{error}</p>}
    </Section>
  );
}

export function ChangePin() {
  const { t, me, onLogin } = useApp();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") && params.get("next")!.startsWith("/") ? params.get("next")! : "/";
  const [oldPin, setOldPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!me) return <Navigate to="/login" replace />;

  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      await api("/auth/pin/change", { method: "POST", body: { old_pin: oldPin || null, new_pin: newPin } });
      const tok = localStorage.getItem("dg_token");
      if (tok) await onLogin(tok); // refresh /me so pin_must_change clears
      nav(next, { replace: true });
    } catch (err) { setError(err instanceof ApiError ? err.message : t("error")); } finally { setBusy(false); }
  }
  return (
    <Section title={t("changePin")}>
      <form onSubmit={save} className="space-y-3">
        {me.pin_must_change && <label className="block space-y-1"><span className="font-semibold">{t("oldPin")}</span>
          <input className="input" type="password" inputMode="numeric" pattern="[0-9]{4,6}" maxLength={6} required value={oldPin} onChange={(e) => setOldPin(e.target.value.replace(/\D/g, ""))} /></label>}
        <label className="block space-y-1"><span className="font-semibold">{t("newPin")}</span>
          <input className="input" type="password" inputMode="numeric" pattern="[0-9]{4,6}" maxLength={6} required value={newPin} onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ""))} /></label>
        <button className="btn btn-primary w-full" disabled={busy}>{t("savePin")}</button>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 font-semibold text-red-700">{error}</p>}
      </form>
    </Section>
  );
}
