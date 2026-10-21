// Pure cart logic (unit-tested). The cart can hold items from several shops; checkout makes one bill per shop.
export type CartLine = {
  storeItemId: number; storeId: number; storeName: string; name: string; nameHi: string | null;
  pricePaise: number; qty: number; imagePath: string | null;
};
export type Cart = CartLine[];
export type ShopGroup = { storeId: number; storeName: string; lines: CartLine[]; subtotalPaise: number };

const MAX_QTY = 100;

export function addItem(cart: Cart, line: Omit<CartLine, "qty">, qty = 1): Cart {
  const existing = cart.find((l) => l.storeItemId === line.storeItemId);
  if (existing) return cart.map((l) => (l === existing ? { ...l, qty: Math.min(MAX_QTY, l.qty + qty) } : l));
  return [...cart, { ...line, qty: Math.min(MAX_QTY, qty) }];
}

export function setQty(cart: Cart, storeItemId: number, qty: number): Cart {
  if (qty <= 0) return cart.filter((l) => l.storeItemId !== storeItemId);
  return cart.map((l) => (l.storeItemId === storeItemId ? { ...l, qty: Math.min(MAX_QTY, qty) } : l));
}

export function groupByShop(cart: Cart): ShopGroup[] {
  const groups = new Map<number, ShopGroup>();
  for (const l of cart) {
    const g = groups.get(l.storeId) ?? { storeId: l.storeId, storeName: l.storeName, lines: [], subtotalPaise: 0 };
    g.lines.push(l);
    g.subtotalPaise += l.pricePaise * l.qty;
    groups.set(l.storeId, g);
  }
  return [...groups.values()];
}

export const cartCount = (cart: Cart) => cart.reduce((n, l) => n + l.qty, 0);
export const cartSubtotal = (cart: Cart) => cart.reduce((n, l) => n + l.pricePaise * l.qty, 0);

/** Drops anything that is not a well-formed line, so a corrupted or old saved cart never crashes the app. */
export function sanitize(raw: unknown): Cart {
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (l): l is CartLine =>
      !!l && Number.isInteger(l.storeItemId) && Number.isInteger(l.storeId) && typeof l.name === "string" &&
      typeof l.storeName === "string" && Number.isInteger(l.pricePaise) && l.pricePaise > 0 && Number.isInteger(l.qty) && l.qty > 0,
  );
}

export function formatMoney(paise: number): string {
  const rupees = paise / 100;
  return "₹" + (Number.isInteger(rupees) ? rupees.toString() : rupees.toFixed(2));
}
