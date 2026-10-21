import { useState } from "react";
import { api, ApiError, type Person } from "../api";
import { suggestPin } from "../agent/Agent";
import { ErrorBox, Section, Spinner, StatusChip } from "../components";
import type { Key } from "../i18n";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

const ROLES = ["merchant", "rider", "agent", "admin", "customer"] as const;
const roleKey = (r: string) => `role${r[0].toUpperCase()}${r.slice(1)}` as Key;

function PersonRow({ p, isMe, onChanged }: { p: Person; isMe: boolean; onChanged: () => void }) {
  const { t } = useApp();
  const [busy, setBusy] = useState(false);
  const [pin, setPin] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function patch(body: Record<string, unknown>) {
    setBusy(true); setError(null);
    try { await api(`/admin/users/${p.id}`, { method: "PATCH", body }); onChanged(); }
    catch (e) { setError(e instanceof ApiError ? e.message : t("error")); } finally { setBusy(false); }
  }
  async function resetPin() { const next = suggestPin(); await patch({ temp_pin: next }); setPin(next); }

  return (
    <li className="card space-y-2 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold">{p.name ?? p.phone ?? p.email}</p>
          <p className="text-sm text-muted">{[p.phone, p.email].filter(Boolean).join(" · ")}</p>
        </div>
        <span className="flex flex-col items-end gap-1">
          <StatusChip text={t(roleKey(p.role))} tone="gray" />
          {!p.active && <StatusChip text={t("disabled")} tone="red" />}
        </span>
      </div>
      <div className="flex gap-2">
        {p.phone && <button className="btn btn-ghost !min-h-10 flex-1" disabled={busy} onClick={() => void resetPin()}>{t("resetPin")}</button>}
        {!isMe && <button className={`btn !min-h-10 flex-1 ${p.active ? "btn-ghost" : "btn-primary"}`} disabled={busy} onClick={() => void patch({ active: !p.active })}>{p.active ? t("disable") : t("enable")}</button>}
      </div>
      {pin && <p className="rounded-xl bg-brand-soft p-3 text-center"><span className="block text-sm">{t("newTempPin")}</span><span className="text-3xl font-extrabold tracking-[0.3em] text-brand">{pin}</span></p>}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
    </li>
  );
}

function AddPerson({ onDone }: { onDone: () => void }) {
  const { t } = useApp();
  const [role, setRole] = useState<(typeof ROLES)[number]>("merchant");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [pin, setPin] = useState(() => suggestPin());
  const [error, setError] = useState<string | null>(null);
  const [made, setMade] = useState<string | null>(null);

  async function save() {
    setError(null); setMade(null);
    try {
      await api("/admin/users", { method: "POST", body: { role, name: name || null, phone: phone || null, email: email || null, temp_pin: phone ? pin : null } });
      setMade(phone ? pin : t("personAdded"));
      setName(""); setPhone(""); setEmail(""); setPin(suggestPin());
      onDone();
    } catch (e) { setError(e instanceof ApiError ? e.message : t("error")); }
  }
  return (
    <div className="card space-y-2 p-3">
      <p className="font-bold">{t("addPerson")}</p>
      <select className="input" aria-label={t("roleLabel")} value={role} onChange={(e) => setRole(e.target.value as (typeof ROLES)[number])}>
        {ROLES.filter((r) => r !== "customer").map((r) => <option key={r} value={r}>{t(roleKey(r))}</option>)}
      </select>
      <input className="input" placeholder={t("yourName")} value={name} onChange={(e) => setName(e.target.value)} />
      <input className="input" inputMode="numeric" maxLength={10} placeholder={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} />
      <input className="input" type="email" placeholder={t("email")} value={email} onChange={(e) => setEmail(e.target.value)} />
      {phone && (
        <div className="flex gap-2">
          <input className="input text-center text-xl tracking-[0.4em]" aria-label={t("tempPin")} inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
          <button type="button" className="btn btn-ghost" onClick={() => setPin(suggestPin())}>↻</button>
        </div>
      )}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      {made && <p className="rounded-xl bg-brand-soft p-3 text-center font-semibold">{phone || /^\d+$/.test(made) ? `${t("tempPin")}: ${made}` : made}</p>}
      <button className="btn btn-primary w-full" onClick={() => void save()}>{t("addPerson")}</button>
    </div>
  );
}

export default function AdminPeople() {
  const { t, me } = useApp();
  const [role, setRole] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const path = `/admin/users?${role ? `role=${role}&` : ""}${q.trim() ? `q=${encodeURIComponent(q.trim())}` : ""}`;
  const res = useFetch<Person[]>(path);

  return (
    <Section title={t("adminPeople")}>
      <button className={`btn w-full ${adding ? "btn-primary" : "btn-ghost"}`} onClick={() => setAdding(!adding)}>{t("addPerson")}</button>
      {adding && <AddPerson onDone={res.reload} />}
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4">
        {[null, ...ROLES].map((r) => (
          <button key={r ?? "all"} onClick={() => setRole(r)} className={`shrink-0 rounded-full px-4 py-2 font-semibold ${role === r ? "bg-brand text-white" : "border border-gray-300 bg-white"}`}>{r ? t(roleKey(r)) : t("filterAll")}</button>
        ))}
      </div>
      <input className="input" type="search" placeholder={t("search2")} value={q} onChange={(e) => setQ(e.target.value)} />
      {res.loading ? <Spinner /> : res.error || !res.data ? <ErrorBox message={res.error ?? "error"} onRetry={res.reload} /> : res.data.length === 0 ? <p className="py-6 text-center text-muted">{t("noPeople")}</p> : (
        <ul className="space-y-2">{res.data.map((p) => <PersonRow key={p.id} p={p} isMe={p.id === me?.id} onChanged={res.reload} />)}</ul>
      )}
    </Section>
  );
}
