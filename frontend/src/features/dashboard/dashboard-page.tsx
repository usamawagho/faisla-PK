"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { User } from "@/types/api";

const roleCopy = {
  client: {
    title: "Your legal journey, organized.",
    intro: "Find counsel, keep track of your appointments, and stay close to case updates.",
    tiles: [
      ["Discover", "Browse verified lawyer profiles.", "/lawyers"],
      ["Appointments", "Manage consultation requests and schedules.", "/dashboard/appointments"],
      ["Cases", "Keep case details and updates together.", "/dashboard/cases"],
      ["Documents", "Open files shared on your cases.", "/dashboard/documents"],
    ],
  },
  lawyer: {
    title: "Your practice, all in one place.",
    intro: "Keep your profile current and manage client work with clarity.",
    tiles: [
      ["Your profile", "Manage the details clients see.", null],
      ["Appointments", "Review requests and manage availability.", "/lawyer/appointments"],
      ["Cases", "Manage case details, notes, and documents.", "/dashboard/cases"],
      ["Documents", "Open files shared on your cases.", "/dashboard/documents"],
    ],
  },
  admin: {
    title: "Platform overview.",
    intro: "Manage users, review lawyer applications, and monitor platform activity.",
    tiles: [
      ["Dashboard", "View platform statistics and activity.", "/admin/dashboard"],
      ["Users", "Review and manage user accounts.", "/admin/users"],
      ["Lawyer review", "Approve or reject pending applications.", "/admin/lawyers"],
    ],
  },
} as const;

export function DashboardPage({ lawyerPortal = false }: { lawyerPortal?: boolean }) {
  const router = useRouter();
  const setUser = useAuthStore((state) => state.setUser);
  const userQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: async () => {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
      return data;
    },
    retry: false,
  });
  const user = userQuery.data;
  const shouldRedirect = Boolean(
    user &&
      (lawyerPortal
        ? user.role !== "lawyer"
        : user.role === "lawyer" || user.role === "admin"),
  );
  const activityQuery = useQuery({
    queryKey: ["dashboard-activity", user?.role],
    enabled: Boolean(user),
    queryFn: async () => {
      if (!user) return null;
      if (user.role === "admin") {
        const { data } = await api.get<{
          total_users: number;
          total_lawyers: number;
          total_clients: number;
          total_cases: number;
          pending_appointments: number;
          approved_lawyers: number;
        }>("/admin/dashboard");
        return data;
      }

      const [appointments, cases] = await Promise.all([
        api.get<unknown[]>(
          user.role === "lawyer" ? "/appointments/lawyer" : "/appointments/my",
        ),
        api.get<unknown[]>("/cases/my"),
      ]);
      return {
        appointments: appointments.data.length,
        cases: cases.data.length,
      };
    },
  });

  useEffect(() => {
    if (userQuery.isError) router.replace("/login");
  }, [userQuery.isError, router]);

  useEffect(() => {
    if (!user || !shouldRedirect) return;
    router.replace(
      user.role === "admin"
        ? "/admin/dashboard"
        : user.role === "lawyer"
          ? "/portal"
          : "/dashboard",
    );
  }, [router, shouldRedirect, user]);

  if (userQuery.isPending || !user || shouldRedirect) {
    return <div className="page-shell"><div className="loading-state">Loading your workspace...</div></div>;
  }

  const content = roleCopy[user.role];
  return (
    <div className="page-shell">
      <div className="eyebrow">{user.role} workspace</div>
      <h1 className="page-title">{content.title}</h1>
      <p className="page-intro">{content.intro}</p>
      {activityQuery.isError && (
        <div className="error-state" role="alert">
          Workspace totals could not be loaded. You can still use the navigation below.
        </div>
      )}
      {!activityQuery.isPending && activityQuery.data && (
        <div className="detail-info-grid">
          {user.role === "admin" && "total_users" in activityQuery.data ? (
            <>
              <Stat label="Total users" value={activityQuery.data.total_users} />
              <Stat label="Lawyers" value={activityQuery.data.total_lawyers} />
              <Stat label="Clients" value={activityQuery.data.total_clients} />
              <Stat label="Cases" value={activityQuery.data.total_cases} />
              <Stat label="Pending appointments" value={activityQuery.data.pending_appointments} />
              <Stat label="Approved lawyers" value={activityQuery.data.approved_lawyers} />
            </>
          ) : "appointments" in activityQuery.data ? (
            <>
              <Stat label="Appointments" value={activityQuery.data.appointments} />
              <Stat label="Cases" value={activityQuery.data.cases} />
            </>
          ) : null}
        </div>
      )}
      <div className="dashboard-grid">
        {content.tiles.map(([title, description, href]) => {
          const card = (
            <>
              <span>{user.role}</span>
              <h2>{title}</h2>
              <p>{description}</p>
            </>
          );
          return href ? (
            <Link className="dashboard-card" href={href} key={title}>{card}</Link>
          ) : (
            <article className="dashboard-card" key={title}>{card}</article>
          );
        })}
      </div>
      <p className="field-help" style={{ marginTop: 18 }}>
        Use the navigation above to manage appointments, cases, documents, and platform access.
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="detail-info">
      <small>{label}</small>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}
