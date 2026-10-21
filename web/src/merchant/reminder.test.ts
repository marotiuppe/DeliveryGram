import { describe, expect, it } from "vitest";
import { reminderMessage, rupeesToPaise, smsLink, whatsappLink } from "./reminder";

describe("khata reminder links", () => {
  it("writes the reminder in Hindi or English with the amount", () => {
    expect(reminderMessage("hi", "रमेश", "Sharma Kirana", 90000)).toContain("₹900");
    expect(reminderMessage("hi", "रमेश", "Sharma Kirana", 90000)).toContain("रमेश");
    expect(reminderMessage("en", null, "Sharma Kirana", 4550)).toBe("Hello, you have ₹45.50 due at Sharma Kirana. Please pay when convenient. Thank you.");
  });

  it("adds the India country code for WhatsApp and encodes the text", () => {
    const link = whatsappLink("98765 43210", "a b&c");
    expect(link).toBe("https://wa.me/919876543210?text=a%20b%26c");
    expect(whatsappLink("+919876543210", "x")).toContain("wa.me/919876543210");
  });

  it("builds an sms link", () => {
    expect(smsLink("9876543210", "hi there")).toBe("sms:9876543210?body=hi%20there");
  });
});

describe("rupeesToPaise", () => {
  it("converts rupees typed by a shopkeeper", () => {
    expect(rupeesToPaise("450")).toBe(45000);
    expect(rupeesToPaise("45.5")).toBe(4550);
    expect(rupeesToPaise("1,200")).toBe(120000);
    expect(rupeesToPaise("19.99")).toBe(1999);
  });
  it("rejects bad input", () => {
    for (const bad of ["", "0", "-5", "abc", "12.345", "1e3"]) expect(rupeesToPaise(bad)).toBeNull();
  });
});
