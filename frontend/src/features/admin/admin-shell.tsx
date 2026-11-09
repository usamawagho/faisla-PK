"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const adminLinks = [
  { href: "/admin/dashboard", label: "Dashboard" },
  { href: "/admin/lawyers", label: "Lawyers" },
  { href: "/admin/users", label: "Users" },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/admin/login") return children;

  return (
    <div className="admin-layout">
      <aside aria-label="Administrator navigation" className="admin-sidebar">
        <Link aria-label="Faisla administration dashboard" className="admin-brand" href="/admin/dashboard">
          <span className="brand-mark">F</span>
          <span>Faisla<span className="brand-country"> Admin</span></span>
        </Link>
        <p>Administration</p>
        <nav>
          {adminLinks.map((link) => (
            <Link
              aria-current={pathname === link.href ? "page" : undefined}
              className={pathname === link.href ? "admin-nav-link is-active" : "admin-nav-link"}
              href={link.href}
              key={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="admin-content">{children}</div>
    </div>
  );
}
