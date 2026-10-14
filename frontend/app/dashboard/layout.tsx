"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ShieldOff } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { PAGE_ACCESS, ROLE_HOME, isRole } from "@/lib/roles";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem("satya_role") || "";
    setRole(stored);
  }, []);

  // Still figuring out who's logged in -- avoid a flash of "access denied"
  // before we've even read localStorage.
  if (role === null) {
    return (
      <div className="flex min-h-screen bg-ink-950">
        <Sidebar />
        <div className="flex-1 overflow-x-hidden p-4" />
      </div>
    );
  }

  const allowedRoles = PAGE_ACCESS[pathname];
  const isAllowed = !allowedRoles || (isRole(role) && allowedRoles.includes(role));

  return (
    <div className="flex min-h-screen bg-ink-950">
      <Sidebar />
      <div className="flex-1 overflow-x-hidden p-4 sm:p-6">
        {isAllowed ? (
          <div className="glass-card min-h-[calc(100vh-3rem)] overflow-hidden">{children}</div>
        ) : (
          <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-risk-critical/10">
              <ShieldOff className="h-6 w-6 text-risk-critical" />
            </div>
            <div>
              <h1 className="font-display text-xl text-ink_text-900">This page isn't part of your role</h1>
              <p className="mt-2 max-w-sm text-sm text-ink_text-500">
                Your account doesn't have access to this section. If you think this is a mistake,
                ask your Administrator.
              </p>
            </div>
            <Link
              href={isRole(role) ? ROLE_HOME[role] : "/dashboard"}
              className="btn-primary mt-2"
              onClick={(e) => {
                // client-side nav is enough, but ensure we don't get stuck on
                // an already-blocked route if ROLE_HOME itself briefly mismatches
                if (!isRole(role)) {
                  e.preventDefault();
                  router.push("/login");
                }
              }}
            >
              Go to your dashboard
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
