import { useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { imageUrl } from "./api";
import { cartCount, formatMoney } from "./cart";
import { useApp } from "./state";

export function Layout() {
  const { t, lang, setLang, cart, online, me, logout } = useApp();
  const loc = useLocation();
  const count = cartCount(cart);
  const inMerchant = loc.pathname.startsWith("/merchant");
  const inRider = loc.pathname.startsWith("/rider");
  const inAdmin = loc.pathname.startsWith("/admin");
  const isAgent = me?.role === "agent";
  const tab = ({ isActive }: { isActive: boolean }) =>
    `flex-1 flex flex-col items-center justify-center py-2 text-sm font-semibold ${isActive ? "text-brand" : "text-gray-500"}`;
  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col bg-paper">
      <header className="sticky top-0 z-20 flex items-center justify-between bg-brand px-4 py-3 text-white">
        <Link to="/" className="text-lg font-bold">{t("appName")}</Link>
        <div className="flex items-center gap-2">
          <button className="rounded-lg bg-white/20 px-3 py-1.5 text-sm font-semibold" onClick={() => setLang(lang === "hi" ? "en" : "hi")} aria-label={t("language")}>
            {lang === "hi" ? "English" : "हिन्दी"}
          </button>
          {me ? <button className="rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-brand" onClick={logout}>{t("logout")}</button> : <Link to={`/login?next=${encodeURIComponent(loc.pathname)}`} className="rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-brand">{t("login")}</Link>}
        </div>
      </header>
      {!online && <div role="status" className="bg-amber-100 px-4 py-2 text-sm text-amber-900">{t("offline")}</div>}
      <main className="flex-1 px-4 py-4 pb-24"><Outlet /></main>
      <nav className="fixed bottom-0 left-0 right-0 z-20 mx-auto flex max-w-xl border-t border-gray-200 bg-white" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        {inAdmin ? (<>
          <NavLink to="/admin" end className={tab}><span aria-hidden>📊</span>{t("adminHome")}</NavLink>
          <NavLink to="/admin/shops" className={tab}><span aria-hidden>🏪</span>{t("adminShops")}</NavLink>
          <NavLink to="/admin/people" className={tab}><span aria-hidden>👥</span>{t("adminPeople")}</NavLink>
          <NavLink to="/admin/villages" className={tab}><span aria-hidden>🏘️</span>{t("adminVillages")}</NavLink>
          <NavLink to="/admin/rates" className={tab}><span aria-hidden>％</span>{t("adminRates")}</NavLink>
        </>) : inRider ? (<>
          <NavLink to="/rider" end className={tab}><span aria-hidden>🛵</span>{t("riderHome")}</NavLink>
        </>) : inMerchant ? (<>
          <NavLink to="/merchant" end className={tab}><span aria-hidden>🧾</span>{t("merchantOrders")}</NavLink>
          <NavLink to="/merchant/items" className={tab}><span aria-hidden>🧺</span>{t("merchantItems")}</NavLink>
          <NavLink to="/merchant/khata" className={tab}><span aria-hidden>📒</span>{t("merchantKhata")}</NavLink>
        </>) : isAgent ? (<>
          <NavLink to="/" end className={tab}><span aria-hidden>🏪</span>{t("home")}</NavLink>
          <NavLink to="/search" className={tab}><span aria-hidden>🔍</span>{t("search")}</NavLink>
          <NavLink to="/cart" className={tab}><span aria-hidden className="relative">🛒{count > 0 && <b className="absolute -right-3 -top-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{count}</b>}</span>{t("cart")}</NavLink>
          <NavLink to="/agent" end className={tab}><span aria-hidden>📋</span>{t("orders")}</NavLink>
          <NavLink to="/agent/register" className={tab}><span aria-hidden>🧑‍🌾</span>{t("registerVillager").split(" ")[0]}</NavLink>
        </>) : (<>
        <NavLink to="/" end className={tab}><span aria-hidden>🏪</span>{t("home")}</NavLink>
        <NavLink to="/search" className={tab}><span aria-hidden>🔍</span>{t("search")}</NavLink>
        <NavLink to="/cart" className={tab}>
          <span aria-hidden className="relative">🛒{count > 0 && <b className="absolute -right-3 -top-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{count}</b>}</span>{t("cart")}
        </NavLink>
        <NavLink to="/orders" className={tab}><span aria-hidden>📦</span>{t("orders")}</NavLink>
        <NavLink to="/khata" className={tab}><span aria-hidden>📒</span>{t("khata")}</NavLink>
        </>)}
      </nav>
    </div>
  );
}

export function Spinner() {
  const { t } = useApp();
  return <p role="status" className="py-10 text-center text-gray-500">{t("loading")}</p>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useApp();
  return (
    <div role="alert" className="card space-y-3 p-4 text-center">
      <p className="text-red-700">{message === "offline" ? t("offline") : message}</p>
      {onRetry && <button className="btn btn-ghost" onClick={onRetry}>{t("retry")}</button>}
    </div>
  );
}

export function ItemImage({ path, alt, size = 64 }: { path: string | null; alt: string; size?: number }) {
  const [broken, setBroken] = useState(false);
  const src = imageUrl(path);
  const box = { width: size, height: size };
  if (!src || broken) return <div className="flex shrink-0 items-center justify-center rounded-xl bg-brand-soft text-2xl" style={box} aria-hidden>🧺</div>;
  return <img src={src} alt={alt} loading="lazy" onError={() => setBroken(true)} className="shrink-0 rounded-xl object-cover" style={box} />;
}

export function Stepper({ qty, onChange }: { qty: number; onChange: (q: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      <button className="btn btn-ghost !min-h-10 !px-3" onClick={() => onChange(qty - 1)} aria-label="-">−</button>
      <span className="w-8 text-center text-lg font-bold" aria-live="polite">{qty}</span>
      <button className="btn btn-ghost !min-h-10 !px-3" onClick={() => onChange(qty + 1)} aria-label="+">+</button>
    </div>
  );
}

export const Price = ({ paise }: { paise: number }) => <span className="font-bold">{formatMoney(paise)}</span>;

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (<section className="space-y-3"><h1 className="text-xl font-bold">{title}</h1>{children}</section>);
}

export function StatusChip({ text, tone }: { text: string; tone: "green" | "amber" | "red" | "gray" }) {
  const cls = { green: "bg-green-100 text-green-800", amber: "bg-amber-100 text-amber-900", red: "bg-red-100 text-red-800", gray: "bg-gray-100 text-gray-700" }[tone];
  return <span className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${cls}`}>{text}</span>;
}
