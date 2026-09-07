import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../lib/auth";
import type { Role } from "../lib/types";

interface NavItem {
  to: string;
  label: string;
  roles: Role[];
}

const ALL: Role[] = ["SUPER_ADMIN", "ADMIN", "SECURITY_GUARD", "EMPLOYEE"];
const STAFF: Role[] = ["SUPER_ADMIN", "ADMIN", "SECURITY_GUARD"];
const ADMINS: Role[] = ["SUPER_ADMIN", "ADMIN"];

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", roles: STAFF },
  { to: "/scan", label: "Gate verification", roles: STAFF },
  { to: "/inside", label: "Currently inside", roles: STAFF },
  { to: "/deliveries", label: "Deliveries", roles: STAFF },
  { to: "/visitors", label: "Visitors", roles: STAFF },
  { to: "/employees", label: "Employees", roles: STAFF },
  { to: "/gates", label: "Gates", roles: ADMINS },
  { to: "/logs", label: "Access logs", roles: STAFF },
  { to: "/reports", label: "Reports", roles: ADMINS },
  { to: "/audit", label: "Audit trail", roles: ADMINS },
  { to: "/my-pass", label: "My pass", roles: ALL },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const items = NAV.filter((item) => user && item.roles.includes(user.role));

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="no-print sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded bg-brand-600 text-sm font-bold text-white">
              GA
            </span>
            <span className="text-sm font-semibold text-slate-900">Gate Access Management</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-slate-500 sm:inline">
              {user?.full_name} · {user?.role.replace("_", " ").toLowerCase()}
            </span>
            <button
              className="btn-secondary"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-2 pb-2">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
