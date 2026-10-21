import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Layout, Spinner } from "./components";
import { useApp } from "./state";

// Each screen is its own chunk so the first load stays small on slow networks.
const Home = lazy(() => import("./pages/Home"));
const Shop = lazy(() => import("./pages/Shop"));
const Search = lazy(() => import("./pages/Search"));
const Cart = lazy(() => import("./pages/Cart"));
const Checkout = lazy(() => import("./pages/Checkout"));
const Khata = lazy(() => import("./pages/Khata"));
const Login = lazy(() => import("./pages/Login"));
const ChangePin = lazy(() => import("./pages/Login").then((m) => ({ default: m.ChangePin })));
const MerchantOrders = lazy(() => import("./merchant/MerchantOrders"));
const MerchantItems = lazy(() => import("./merchant/MerchantItems"));
const MerchantKhata = lazy(() => import("./merchant/MerchantKhata"));
const RiderJobs = lazy(() => import("./rider/RiderJobs"));
const RiderTrip = lazy(() => import("./rider/RiderTrip"));
const AgentHome = lazy(() => import("./agent/Agent").then((m) => ({ default: m.AgentHome })));
const RegisterVillager = lazy(() => import("./agent/Agent").then((m) => ({ default: m.RegisterVillager })));
const AdminDashboard = lazy(() => import("./admin/AdminDashboard"));
const AdminShops = lazy(() => import("./admin/AdminShops"));
const AdminPeople = lazy(() => import("./admin/AdminPeople"));
const AdminVillages = lazy(() => import("./admin/AdminVillages"));
const AdminRates = lazy(() => import("./admin/AdminRates"));
const OrdersList = lazy(() => import("./pages/Orders").then((m) => ({ default: m.OrdersList })));
const DeliveryDetail = lazy(() => import("./pages/Orders").then((m) => ({ default: m.DeliveryDetail })));

type Role = "customer" | "merchant" | "rider" | "agent" | "admin";

/** Screens for one or more roles. Every role has screens: customer, shopkeeper, rider, village helper (agent) and admin. */
function RequireRole({ role, children }: { role: Role | Role[]; children: ReactNode }) {
  const { me, meLoading, t } = useApp();
  const loc = useLocation();
  if (meLoading) return <Spinner />;
  if (!me) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (me.pin_must_change) return <Navigate to={`/change-pin?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (!(Array.isArray(role) ? role : [role]).includes(me.role as Role)) {
    if (["merchant", "rider", "agent", "admin"].includes(me.role)) return <Navigate to={`/${me.role}`} replace />;
    return <p className="card p-4 text-center">{t("staffSoon")}</p>;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="shop/:id" element={<Shop />} />
          <Route path="search" element={<Search />} />
          <Route path="cart" element={<Cart />} />
          <Route path="login" element={<Login />} />
          <Route path="change-pin" element={<ChangePin />} />
          <Route path="checkout" element={<RequireRole role={["customer", "agent"]}><Checkout /></RequireRole>} />
          <Route path="orders" element={<RequireRole role="customer"><OrdersList /></RequireRole>} />
          <Route path="orders/:id" element={<RequireRole role="customer"><DeliveryDetail /></RequireRole>} />
          <Route path="khata" element={<RequireRole role="customer"><Khata /></RequireRole>} />
          <Route path="merchant" element={<RequireRole role="merchant"><MerchantOrders /></RequireRole>} />
          <Route path="merchant/items" element={<RequireRole role="merchant"><MerchantItems /></RequireRole>} />
          <Route path="merchant/khata" element={<RequireRole role="merchant"><MerchantKhata /></RequireRole>} />
          <Route path="agent" element={<RequireRole role="agent"><AgentHome /></RequireRole>} />
          <Route path="agent/register" element={<RequireRole role="agent"><RegisterVillager /></RequireRole>} />
          <Route path="agent/orders/:id" element={<RequireRole role="agent"><DeliveryDetail /></RequireRole>} />
          <Route path="admin" element={<RequireRole role="admin"><AdminDashboard /></RequireRole>} />
          <Route path="admin/shops" element={<RequireRole role="admin"><AdminShops /></RequireRole>} />
          <Route path="admin/people" element={<RequireRole role="admin"><AdminPeople /></RequireRole>} />
          <Route path="admin/villages" element={<RequireRole role="admin"><AdminVillages /></RequireRole>} />
          <Route path="admin/rates" element={<RequireRole role="admin"><AdminRates /></RequireRole>} />
          <Route path="rider" element={<RequireRole role="rider"><RiderJobs /></RequireRole>} />
          <Route path="rider/:id" element={<RequireRole role="rider"><RiderTrip /></RequireRole>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
