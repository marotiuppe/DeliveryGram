import { useState } from "react";
import type { KhataAccount, KhataEntry } from "../api";
import { formatMoney } from "../cart";
import { ErrorBox, Price, Section, Spinner } from "../components";
import { useApp } from "../state";
import { useFetch } from "../useFetch";

function Entries({ storeId }: { storeId: number }) {
  const { t } = useApp();
  const res = useFetch<KhataEntry[]>(`/khata/${storeId}/entries`);
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  return (
    <ul className="divide-y text-sm">
      {res.data.map((e) => (
        <li key={e.id} className="flex justify-between py-2">
          <span>{new Date(e.created_at).toLocaleDateString()} · {e.kind === "SALE" ? t("sale") : t("payment")}{e.note ? ` · ${e.note}` : ""}</span>
          <span className={e.amount_paise > 0 ? "font-semibold text-red-700" : "font-semibold text-green-700"}>{e.amount_paise > 0 ? "+" : "−"}{formatMoney(Math.abs(e.amount_paise))}</span>
        </li>
      ))}
    </ul>
  );
}

export default function Khata() {
  const { t } = useApp();
  const res = useFetch<KhataAccount[]>("/khata");
  const [open, setOpen] = useState<number | null>(null);
  if (res.loading) return <Spinner />;
  if (res.error || !res.data) return <ErrorBox message={res.error ?? "error"} onRetry={res.reload} />;
  return (
    <Section title={t("khataTitle")}>
      {res.data.length === 0 ? <p className="card p-4 text-center text-muted">{t("khataEmpty")}</p> : (
        <ul className="space-y-3">
          {res.data.map((a) => (
            <li key={a.store_id} className="card space-y-2 p-4">
              <button className="flex w-full items-center justify-between text-left" onClick={() => setOpen(open === a.store_id ? null : a.store_id)} aria-expanded={open === a.store_id}>
                <span>
                  <span className="block text-lg font-bold">{a.store_name}</span>
                  <span className="text-sm text-muted">{t("creditLimit")} {formatMoney(a.credit_limit_paise)}{!a.enabled ? ` · ${t("paused")}` : ""}</span>
                </span>
                <span className="text-right"><span className="block text-sm text-muted">{t("youOwe")}</span><Price paise={a.balance_paise} /></span>
              </button>
              {open === a.store_id && <div><p className="mb-1 font-semibold">{t("history")}</p><Entries storeId={a.store_id} /></div>}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
