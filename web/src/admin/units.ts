// Admin screens show percentages and rupees; the API stores basis points (100 = 1%) and paise.

/** "5", "5.5", "12.25" -> basis points. Returns null for empty or invalid input; allows 0. */
export function percentToBps(input: string): number | null {
  const clean = input.trim().replace(/%$/, "");
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  return Math.round(parseFloat(clean) * 100);
}

export function bpsToPercent(bps: number): string {
  const p = bps / 100;
  return Number.isInteger(p) ? String(p) : p.toFixed(2).replace(/0+$/, "");
}

/** Fee typed in rupees; empty means "use the default". Returns undefined for invalid input. */
export function feeToPaise(input: string): number | null | undefined {
  const clean = input.replace(/,/g, "").trim();
  if (clean === "") return null;
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return undefined;
  return Math.round(parseFloat(clean) * 100);
}
