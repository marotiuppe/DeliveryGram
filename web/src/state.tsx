import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getToken, setToken, type Me } from "./api";
import { addItem, sanitize, setQty as setLineQty, type Cart, type CartLine } from "./cart";
import { translate, type Key, type Lang } from "./i18n";

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function save(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode / full storage: keep working in memory */ }
}

type AppState = {
  lang: Lang; setLang: (l: Lang) => void; t: (k: Key) => string;
  villageId: number | null; setVillageId: (id: number) => void;
  cart: Cart; addToCart: (line: Omit<CartLine, "qty">) => void; setQty: (storeItemId: number, qty: number) => void; clearCart: () => void;
  me: Me | null; meLoading: boolean; onLogin: (token: string) => Promise<Me | null>; logout: () => void;
  online: boolean;
};

const Ctx = createContext<AppState | null>(null);
export const useApp = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppProvider");
  return v;
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => load<Lang>("dg_lang", "hi"));
  const [villageId, setVillageState] = useState<number | null>(() => load<number | null>("dg_village", null));
  const [cart, setCart] = useState<Cart>(() => sanitize(load<unknown>("dg_cart", [])));
  const [me, setMe] = useState<Me | null>(null);
  const [meLoading, setMeLoading] = useState<boolean>(() => !!getToken());
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));

  useEffect(() => {
    const up = () => setOnline(true), down = () => setOnline(false);
    window.addEventListener("online", up); window.addEventListener("offline", down);
    return () => { window.removeEventListener("online", up); window.removeEventListener("offline", down); };
  }, []);

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  useEffect(() => save("dg_cart", cart), [cart]); // the cart survives reloads and dropped connections

  const onLogin = useCallback(async (token: string) => {
    setToken(token);
    setMeLoading(true);
    try {
      const m = await api<Me>("/me");
      setMe(m);
      return m;
    } catch {
      setToken(null);
      setMe(null);
      return null;
    } finally {
      setMeLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = getToken();
    if (token) void onLogin(token);
  }, [onLogin]);

  const value = useMemo<AppState>(() => ({
    lang, setLang: (l) => { setLangState(l); save("dg_lang", l); }, t: (k) => translate(lang, k),
    villageId, setVillageId: (id) => { setVillageState(id); save("dg_village", id); },
    cart, addToCart: (line) => setCart((c) => addItem(c, line)), setQty: (id, q) => setCart((c) => setLineQty(c, id, q)), clearCart: () => setCart([]),
    me, meLoading, onLogin, logout: () => { setToken(null); setMe(null); }, online,
  }), [lang, villageId, cart, me, meLoading, onLogin, online]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
