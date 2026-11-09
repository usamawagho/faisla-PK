"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { User } from "@/types/api";
import type { Notification } from "@/types/workflows";

const publicLinks = [
  { href: "/lawyers", label: "Find a lawyer" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, setUser, clear } = useAuthStore();
  const [error, setError] = useState("");

  const notifications = useQuery({
    queryKey: ["notifications", user?.id],
    enabled: Boolean(user),
    queryFn: async () => (await api.get<Notification[]>("/notifications?limit=100")).data,
  });
  const unreadCount = notifications.data?.filter((item) => !item.is_read).length ?? 0;

  useEffect(() => {
    let active = true;
    api
      .get<User>("/auth/me")
      .then(({ data }) => {
        if (active) setUser(data);
      })
      .catch(() => {
        if (active) setUser(null);
      });
    return () => {
      active = false;
    };
  }, [pathname, setUser]);

  async function logout() {
    setError("");
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      queryClient.clear();
      clear();
      router.push("/");
      router.refresh();
    } catch (logoutError) {
      setError(getApiError(logoutError, "Could not log out. Please try again."));
    }
  }

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/" aria-label="Faisla PK home">
          <span className="brand-mark">F</span>
          <span>faisla<span className="brand-country">.pk</span></span>
        </Link>
        <nav className="main-nav" aria-label="Main navigation">
          {publicLinks.map((link) => (
            <Link
              aria-current={pathname.startsWith(link.href) ? "page" : undefined}
              href={link.href}
              key={link.href}
            >
              {link.label}
            </Link>
          ))}
          {user ? (
            <>
              <Link className="nav-dashboard" href="/dashboard">Dashboard</Link>
              <Link href="/dashboard/notifications" aria-label={unreadCount ? `${unreadCount} unread notifications` : "Notifications"}>
                Notifications{unreadCount > 0 ? ` (${unreadCount})` : ""}
              </Link>
              <button className="link-button" onClick={logout} type="button">Sign out</button>
            </>
          ) : (
            <>
              <Link href="/login">Sign in</Link>
              <Link className="button button-small" href="/register">Get started</Link>
            </>
          )}
        </nav>
      </div>
      {error && <div className="header-error" role="alert">{error}</div>}
    </header>
  );
}
