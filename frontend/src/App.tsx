import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import Layout from "./components/Layout";
import { useAuth } from "./lib/auth";
import type { Role } from "./lib/types";
import Audit from "./pages/Audit";
import Dashboard from "./pages/Dashboard";
import Deliveries from "./pages/Deliveries";
import Employees from "./pages/Employees";
import Gates from "./pages/Gates";
import Inside from "./pages/Inside";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import MyPass from "./pages/MyPass";
import PublicPass from "./pages/PublicPass";
import Reports from "./pages/Reports";
import Scan from "./pages/Scan";
import Visitors from "./pages/Visitors";

const STAFF: Role[] = ["SUPER_ADMIN", "ADMIN", "SECURITY_GUARD"];
const ADMINS: Role[] = ["SUPER_ADMIN", "ADMIN"];

function Guard({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="grid min-h-screen place-items-center text-slate-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/my-pass" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* Pass links handed to visitors and drivers. */}
      <Route path="/d/:token" element={<PublicPass />} />
      <Route path="/v/:token" element={<PublicPass />} />
      <Route path="/q/:token" element={<PublicPass />} />

      <Route
        element={
          <Guard>
            <Layout />
          </Guard>
        }
      >
        <Route path="/" element={<Guard roles={STAFF}><Dashboard /></Guard>} />
        <Route path="/scan" element={<Guard roles={STAFF}><Scan /></Guard>} />
        <Route path="/inside" element={<Guard roles={STAFF}><Inside /></Guard>} />
        <Route path="/deliveries" element={<Guard roles={STAFF}><Deliveries /></Guard>} />
        <Route path="/visitors" element={<Guard roles={STAFF}><Visitors /></Guard>} />
        <Route path="/employees" element={<Guard roles={STAFF}><Employees /></Guard>} />
        <Route path="/gates" element={<Guard roles={ADMINS}><Gates /></Guard>} />
        <Route path="/logs" element={<Guard roles={STAFF}><Logs /></Guard>} />
        <Route path="/reports" element={<Guard roles={ADMINS}><Reports /></Guard>} />
        <Route path="/audit" element={<Guard roles={ADMINS}><Audit /></Guard>} />
        <Route path="/my-pass" element={<MyPass />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
