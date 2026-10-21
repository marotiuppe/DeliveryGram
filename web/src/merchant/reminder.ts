// Khata reminders as free tap-to-send links: no SMS provider, no WhatsApp API fees. The shopkeeper taps and presses send.
import type { Lang } from "../i18n";
import { formatMoney } from "../cart";

export function reminderMessage(lang: Lang, customerName: string | null, storeName: string, duePaise: number): string {
  const amount = formatMoney(duePaise);
  if (lang === "hi") return `नमस्ते${customerName ? " " + customerName : ""}, ${storeName} में आपका ${amount} बकाया है। कृपया सुविधा से जमा कर दें। धन्यवाद।`;
  return `Hello${customerName ? " " + customerName : ""}, you have ${amount} due at ${storeName}. Please pay when convenient. Thank you.`;
}

const digits = (phone: string) => phone.replace(/\D/g, "");

/** Indian mobile numbers are 10 digits; wa.me needs the country code. */
export function whatsappLink(phone: string, message: string): string {
  const d = digits(phone);
  const full = d.length === 10 ? "91" + d : d;
  return `https://wa.me/${full}?text=${encodeURIComponent(message)}`;
}

export function smsLink(phone: string, message: string): string {
  return `sms:${digits(phone)}?body=${encodeURIComponent(message)}`;
}

/** "450", "450.5", "1,200" -> paise. Returns null for empty, zero, negative or non-numeric input. */
export function rupeesToPaise(input: string): number | null {
  const clean = input.replace(/,/g, "").trim();
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const paise = Math.round(parseFloat(clean) * 100);
  return paise > 0 ? paise : null;
}
