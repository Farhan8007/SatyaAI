"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import {
  ShieldCheck,
  LayoutDashboard,
  FileText,
  AlertTriangle,
  ScrollText,
  FileSearch,
  Users,
  Settings,
  LogOut,
} from "lucide-react";
import { PAGE_ACCESS, isRole } from "@/lib/roles";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/papers", label: "Question Papers", icon: FileText },
  { href: "/dashboard/alerts", label: "AI Alerts", icon: AlertTriangle },
  { href: "/dashboard/audit-logs", label: "Audit Logs", icon: ScrollText },
  { href: "/dashboard/reports", label: "Investigation Reports", icon: FileSearch },
  { href: "/dashboard/users", label: "User Management", icon: Users },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState("");

  useEffect(() => {
    setRole(window.localStorage.getItem("satya_role") || "");
  }, []);

  function handleLogout() {
    window.localStorage.removeItem("satya_token");
    window.localStorage.removeItem("satya_role");
    window.localStorage.removeItem("satya_name");
    router.push("/login");
  }

  const visibleNav = NAV.filter((item) => {
    if (!isRole(role)) return true; // role not loaded yet -- avoid a flash of an empty sidebar
    return PAGE_ACCESS[item.href]?.includes(role);
  });

  return (
    <aside className="hidden w-64 shrink-0 flex-col rounded-3xl bg-sidebar-gradient px-4 py-6 shadow-card-lg sm:m-4 sm:mr-0 sm:flex">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/15">
          <ShieldCheck className="h-4.5 w-4.5 text-white" />
        </div>
        <span className="font-display text-base tracking-tight text-white">SATYA AI</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1.5">
        {visibleNav.map((item) => {
          const active = item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-colors duration-200",
                active ? "text-signal" : "text-white/75 hover:bg-white/10 hover:text-white"
              )}
            >
              {active && (
                <motion.span
                  layoutId="active-nav-pill"
                  className="absolute inset-0 rounded-2xl bg-white shadow-card"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              )}
              <item.icon className="relative z-10 h-4 w-4" />
              <span className="relative z-10">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <button
        onClick={handleLogout}
        className="mt-4 flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium text-white/75 transition-colors duration-200 hover:bg-white/10 hover:text-white"
      >
        <LogOut className="h-4 w-4" />
        Log out
      </button>
    </aside>
  );
}
