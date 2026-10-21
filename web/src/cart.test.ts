import { describe, expect, it } from "vitest";
import { addItem, cartCount, cartSubtotal, formatMoney, groupByShop, sanitize, setQty } from "./cart";
import { translate } from "./i18n";

const atta = { storeItemId: 1, storeId: 10, storeName: "Sharma Kirana", name: "Wheat Atta", nameHi: "आटा", pricePaise: 45000, imagePath: null };
const pickle = { storeItemId: 2, storeId: 20, storeName: "Verma General", name: "Pickle", nameHi: null, pricePaise: 15000, imagePath: null };

describe("cart", () => {
  it("adds, merges the same item and caps quantity", () => {
    let c = addItem([], atta);
    c = addItem(c, atta, 2);
    expect(c).toHaveLength(1);
    expect(c[0].qty).toBe(3);
    expect(addItem(c, atta, 500)[0].qty).toBe(100);
  });

  it("removes a line when quantity reaches zero", () => {
    const c = addItem(addItem([], atta), pickle);
    expect(setQty(c, 1, 0).map((l) => l.storeItemId)).toEqual([2]);
    expect(setQty(c, 2, 5).find((l) => l.storeItemId === 2)?.qty).toBe(5);
  });

  it("groups lines per shop so checkout can make one bill per shop", () => {
    const c = addItem(addItem(addItem([], atta, 2), pickle), { ...atta, storeItemId: 3, name: "Sugar", pricePaise: 5000 });
    const groups = groupByShop(c);
    expect(groups.map((g) => [g.storeName, g.subtotalPaise])).toEqual([["Sharma Kirana", 95000], ["Verma General", 15000]]);
    expect(cartSubtotal(c)).toBe(110000);
    expect(cartCount(c)).toBe(4);
  });

  it("ignores corrupted saved carts", () => {
    expect(sanitize("junk")).toEqual([]);
    expect(sanitize([{ storeItemId: "x" }, null, { ...atta, qty: 2 }, { ...atta, qty: 0 }, { ...atta, qty: 1, pricePaise: -5 }])).toHaveLength(1);
  });

  it("formats rupees without noise", () => {
    expect(formatMoney(45000)).toBe("₹450");
    expect(formatMoney(4550)).toBe("₹45.50");
  });
});

describe("i18n", () => {
  it("uses Hindi when available and falls back to English", () => {
    expect(translate("hi", "cart")).toBe("टोकरी");
    expect(translate("en", "cart")).toBe("Cart");
    expect(translate("hi", "appName")).toBe("DeliveryGram"); // no Hindi entry -> English
  });
});
