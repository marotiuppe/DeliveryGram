import { describe, expect, it } from "vitest";
import { suggestPin } from "./Agent";

describe("suggestPin", () => {
  it("makes 4-digit PINs that are never all-same or a running sequence", () => {
    for (let i = 0; i < 2000; i++) {
      const pin = suggestPin();
      expect(pin).toMatch(/^\d{4}$/);
      expect(/^(\d)\1{3}$/.test(pin)).toBe(false);
      expect(["0123", "1234", "2345", "3456", "4567", "5678", "6789", "3210", "4321", "5432", "6543", "7654", "8765", "9876"]).not.toContain(pin);
    }
  });
  it("is not constant", () => {
    expect(new Set(Array.from({ length: 50 }, () => suggestPin())).size).toBeGreaterThan(10);
  });
});
