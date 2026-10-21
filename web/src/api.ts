// Thin API client. Token lives in localStorage; every failure becomes an ApiError with a readable message.
const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";
const TOKEN_KEY = "dg_token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const getToken = () => {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
};
export const setToken = (t: string | null) => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ }
};
export const imageUrl = (path: string | null | undefined) => (path ? BASE + path : null);

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, { method: init.method ?? "GET", headers, body: init.body !== undefined ? JSON.stringify(init.body) : undefined });
  } catch {
    throw new ApiError(0, "offline");
  }
  if (res.status === 401 && token) setToken(null); // expired or revoked: force a fresh login
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? "Please check the form" : detail;
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// ---- types (mirror backend/app/schemas.py) ----
export type StoreType = { id: number; code: string; name: string; name_hi: string | null; needs_prescription: boolean; has_time_slots: boolean; catalog_mode: string; safety_notice: string | null };
export type Ward = { id: number; number: number; name: string | null };
export type Village = { id: number; name: string; district: string | null; state: string | null; wards: Ward[]; delivery_fee_paise: number; min_order_paise: number };
export type Store = { id: number; name: string; store_type_id: number; village_id: number; phone: string | null; is_open: boolean };
export type StoreItem = { id: number; store_id: number; catalog_item_id: number | null; name: string; name_hi: string | null; price_paise: number; available: boolean; requires_prescription: boolean; image_path: string | null };
export type SearchHit = { store_item_id: number; store_id: number; store_name: string; name: string; name_hi: string | null; price_paise: number; image_path: string | null; requires_prescription: boolean };
export type OrderLine = { store_item_id: number; name: string; unit_price_paise: number; quantity: number };
export type Order = { id: number; delivery_id: number; status: string; store_id: number; store_name: string; store_phone: string | null; payment_method: string; fulfillment: string; prescription_ref: string | null; source: string; contact_phone: string; landmark: string; subtotal_paise: number; tax_paise: number; total_paise: number; items: OrderLine[] };
export type Delivery = {
  id: number; status: string; created_at: string; contact_phone: string; village_id: number; village_name: string; ward_id: number | null; ward_number: number | null; landmark: string; address_details: string | null;
  delivery_fee_paise: number; delivery_code_required: boolean; delivery_code: string | null; rider_id: number | null; orders: Order[];
  bills_total_paise: number; grand_total_paise: number; cash_to_collect_paise: number;
};
export type KhataAccount = { store_id: number; store_name: string; customer_id: number; customer_name: string | null; customer_phone: string | null; credit_limit_paise: number; enabled: boolean; balance_paise: number };
export type KhataEntry = { id: number; kind: string; amount_paise: number; order_id: number | null; note: string | null; created_at: string };
export type AdminStats = {
  orders_today: number; orders_by_status: Record<string, number>; delivered_sales_paise: number; commission_paise: number; delivery_fees_paise: number;
  open_deliveries: number; khata_outstanding_paise: number; shops: number; riders: number; villagers: number;
};
export type SystemInfo = {
  version: string; environment: string; database: string; email_backend: string; email_configured: boolean; last_email_error: string;
  keepalive_enabled: boolean; keepalive_url: string; keepalive_last_ok: boolean | null; keepalive_last_error: string;
};
export type Person = { id: number; role: string; name: string | null; phone: string | null; email: string | null; active: boolean; has_pin: boolean };
export type AdminStore = {
  id: number; name: string; store_type_id: number; store_type_name: string; village_id: number; village_name: string; owner_id: number | null; owner_phone: string | null;
  phone: string | null; address_text: string | null; is_open: boolean; fssai_no: string | null; drug_licence_no: string | null;
  commission_bps: number | null; effective_commission_bps: number; active: boolean;
};
export type Rate = { id: number; code: string; name: string; name_hi: string | null; needs_prescription: boolean; has_time_slots: boolean; commission_bps: number; tax_bps: number; safety_notice: string | null };
export type CustomerLookup = { registered: boolean; name: string | null; has_pin: boolean };
export type Me = { id: number; role: string; name: string | null; phone: string | null; email: string | null; pin_must_change: boolean };
export type TokenOut = { access_token: string; role: string; pin_must_change: boolean };
