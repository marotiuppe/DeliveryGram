import { describe, expect, it } from "vitest";
import { bpsToPercent, feeToPaise, percentToBps } from "./units";

describe("percent <-> basis points", () => {
  it("converts what an owner types", () => {
    expect(percentToBps("5")).toBe(500);
    expect(percentToBps("5.5")).toBe(550);
    expect(percentToBps("12.25%")).toBe(1225);
    expect(percentToBps("0")).toBe(0);
  });
  it("rejects nonsense", () => {
    for (const bad of ["", "abc", "-1", "5.555", "1e2"]) expect(percentToBps(bad)).toBeNull();
  });
  it("shows basis points without noise", () => {
    expect(bpsToPercent(500)).toBe("5");
    expect(bpsToPercent(550)).toBe("5.5");
    expect(bpsToPercent(1225)).toBe("12.25");
    expect(bpsToPercent(0)).toBe("0");
  });
  it("round-trips", () => {
    for (const bps of [0, 50, 500, 725, 1000, 2800]) expect(percentToBps(bpsToPercent(bps))).toBe(bps);
  });
});

describe("delivery fee input", () => {
  it("empty means use the default fee", () => expect(feeToPaise("")).toBeNull());
  it("converts rupees", () => {
    expect(feeToPaise("20")).toBe(2000);
    expect(feeToPaise("12.5")).toBe(1250);
    expect(feeToPaise("0")).toBe(0); // free delivery is valid
  });
  it("flags bad input", () => expect(feeToPaise("abc")).toBeUndefined());
});
