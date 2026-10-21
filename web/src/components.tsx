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
    `relative flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs font-bold ${isActive ? "text-brand before:absolute before:top-0 before:h-1 before:w-10 before:rounded-b-full before:bg-brand" : "text-muted"}`;
  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col bg-paper">
      <header className="sticky top-0 z-20 flex items-center justify-between bg-gradient-to-r from-brand-dark to-brand px-4 py-3 text-white shadow-md">
        <Link to="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight"><span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/20">🛵</span>{t("appName")}</Link>
        <div className="flex items-center gap-2">
          <button className="rounded-lg bg-white/20 px-3 py-1.5 text-sm font-semibold" onClick={() => setLang(lang === "hi" ? "en" : "hi")} aria-label={t("language")}>
            {lang === "hi" ? "English" : "हिन्दी"}
          </button>
          {me ? <button className="rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-brand" onClick={logout}>{t("logout")}</button> : <Link to={`/login?next=${encodeURIComponent(loc.pathname)}`} className="rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-brand">{t("login")}</Link>}
        </div>
      </header>
      {!online && <div role="status" className="bg-amber-100 px-4 py-2 text-sm text-amber-900">{t("offline")}</div>}
      <main className="flex-1 px-4 py-4 pb-24"><Outlet /></main>
      <nav className="fixed bottom-0 left-0 right-0 z-20 mx-auto flex max-w-xl border-t border-line bg-white shadow-[0_-2px_10px_rgb(20_40_25/.06)]" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        {inAdmin ? (<>
          <NavLink to="/admin" end className={tab}><span aria-hidden className="text-xl">📊</span>{t("adminHome")}</NavLink>
          <NavLink to="/admin/shops" className={tab}><span aria-hidden className="text-xl">🏪</span>{t("adminShops")}</NavLink>
          <NavLink to="/admin/people" className={tab}><span aria-hidden className="text-xl">👥</span>{t("adminPeople")}</NavLink>
          <NavLink to="/admin/villages" className={tab}><span aria-hidden className="text-xl">🏘️</span>{t("adminVillages")}</NavLink>
          <NavLink to="/admin/rates" className={tab}><span aria-hidden className="text-xl">％</span>{t("adminRates")}</NavLink>
        </>) : inRider ? (<>
          <NavLink to="/rider" end className={tab}><span aria-hidden className="text-xl">🛵</span>{t("riderHome")}</NavLink>
        </>) : inMerchant ? (<>
          <NavLink to="/merchant" end className={tab}><span aria-hidden className="text-xl">🧾</span>{t("merchantOrders")}</NavLink>
          <NavLink to="/merchant/items" className={tab}><span aria-hidden className="text-xl">🧺</span>{t("merchantItems")}</NavLink>
          <NavLink to="/merchant/khata" className={tab}><span aria-hidden className="text-xl">📒</span>{t("merchantKhata")}</NavLink>
        </>) : isAgent ? (<>
          <NavLink to="/" end className={tab}><span aria-hidden className="text-xl">🏪</span>{t("home")}</NavLink>
          <NavLink to="/search" className={tab}><span aria-hidden className="text-xl">🔍</span>{t("search")}</NavLink>
          <NavLink to="/cart" className={tab}><span aria-hidden className="relative text-xl">🛒{count > 0 && <b className="absolute -right-3 -top-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{count}</b>}</span>{t("cart")}</NavLink>
          <NavLink to="/agent" end className={tab}><span aria-hidden className="text-xl">📋</span>{t("orders")}</NavLink>
          <NavLink to="/agent/register" className={tab}><span aria-hidden className="text-xl">🧑‍🌾</span>{t("registerVillager").split(" ")[0]}</NavLink>
        </>) : (<>
        <NavLink to="/" end className={tab}><span aria-hidden className="text-xl">🏪</span>{t("home")}</NavLink>
        <NavLink to="/search" className={tab}><span aria-hidden className="text-xl">🔍</span>{t("search")}</NavLink>
        <NavLink to="/cart" className={tab}>
          <span aria-hidden className="relative text-xl">🛒{count > 0 && <b className="absolute -right-3 -top-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{count}</b>}</span>{t("cart")}
        </NavLink>
        <NavLink to="/orders" className={tab}><span aria-hidden className="text-xl">📦</span>{t("orders")}</NavLink>
        <NavLink to="/khata" className={tab}><span aria-hidden className="text-xl">📒</span>{t("khata")}</NavLink>
        </>)}
      </nav>
    </div>
  );
}

export function Spinner() {
  const { t } = useApp();
  return <p role="status" className="flex items-center justify-center gap-3 py-10 text-muted"><span aria-hidden className="h-5 w-5 animate-spin rounded-full border-[3px] border-brand-soft border-t-brand" />{t("loading")}</p>;
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
  if (!src || broken) return <div className="flex shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-2xl" style={box} aria-hidden>🧺</div>;
  return <img src={src} alt={alt} loading="lazy" onError={() => setBroken(true)} className="shrink-0 rounded-2xl bg-brand-soft object-cover" style={box} />;
}

export function Stepper({ qty, onChange }: { qty: number; onChange: (q: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      <button className="btn btn-ghost !min-h-11 !min-w-11 !px-0 text-xl" onClick={() => onChange(qty - 1)} aria-label="-">−</button>
      <span className="w-8 text-center text-lg font-bold" aria-live="polite">{qty}</span>
      <button className="btn btn-primary !min-h-11 !min-w-11 !px-0 text-xl" onClick={() => onChange(qty + 1)} aria-label="+">+</button>
    </div>
  );
}

export const Price = ({ paise }: { paise: number }) => <span className="font-bold">{formatMoney(paise)}</span>;

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (<section className="space-y-3"><h1 className="text-2xl font-extrabold">{title}</h1>{children}</section>);
}

export function StatusChip({ text, tone }: { text: string; tone: "green" | "amber" | "red" | "gray" }) {
  const cls = { green: "bg-green-100 text-green-800", amber: "bg-amber-100 text-amber-900", red: "bg-red-100 text-red-800", gray: "bg-gray-100 text-gray-700" }[tone];
  return <span className={`inline-block whitespace-nowrap rounded-full px-3 py-1 text-sm font-bold ${cls}`}>{text}</span>;
}
