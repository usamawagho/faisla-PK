"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, getApiError } from "@/lib/api";
import { useCurrentUser } from "@/features/shared/use-current-user";
import { humanize } from "@/features/shared/format";
import type { AdminStats, AdminUser, PendingLawyer } from "@/types/workflows";

export function AdminDashboardPage() {
  const currentUser = useCurrentUser("admin");
  const stats = useQuery({
    queryKey: ["admin-stats"],
    enabled: currentUser.data?.role === "admin",
    queryFn: async () => (await api.get<AdminStats>("/admin/dashboard")).data,
  });
  if (currentUser.isPending || !currentUser.data) return <div className="page-shell"><div className="loading-state">Loading platform overview...</div></div>;
  if (currentUser.data.role !== "admin") return <div className="page-shell"><div className="loading-state">Redirecting to your workspace...</div></div>;
  return <div className="page-shell">
    <div className="eyebrow">Platform administration</div><h1 className="page-title">Overview</h1>
    <p className="page-intro">Current platform totals from the Faisla API.</p>
    {stats.isPending ? <div className="loading-state">Loading statistics...</div> : stats.isError ? <div className="error-state" role="alert">Dashboard statistics could not be loaded.</div> : (
      <div className="detail-info-grid admin-stat-grid">
        <Stat label="Total users" value={stats.data.total_users} />
        <Stat label="Lawyers" value={stats.data.total_lawyers} />
        <Stat label="Clients" value={stats.data.total_clients} />
        <Stat label="Cases" value={stats.data.total_cases} />
        <Stat label="Pending appointments" value={stats.data.pending_appointments} />
        <Stat label="Approved lawyers" value={stats.data.approved_lawyers} />
      </div>
    )}
  </div>;
}

export function AdminLawyersPage() {
  const currentUser = useCurrentUser("admin");
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const lawyers = useQuery({
    queryKey: ["admin-pending-lawyers"],
    enabled: currentUser.data?.role === "admin",
    queryFn: async () => (await api.get<PendingLawyer[]>("/admin/lawyers/pending")).data,
  });
  async function review(userId: number, decision: "approve" | "reject") {
    setError("");
    try {
      await api.put(`/admin/lawyers/${userId}/${decision}`);
      void queryClient.invalidateQueries({ queryKey: ["admin-pending-lawyers"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    } catch (cause) {
      setError(getApiError(cause, `Could not ${decision} this lawyer.`));
    }
  }
  if (currentUser.isPending || !currentUser.data) return <div className="page-shell"><div className="loading-state">Loading lawyer applications...</div></div>;
  if (currentUser.data.role !== "admin") return <div className="page-shell"><div className="loading-state">Redirecting to your workspace...</div></div>;
  return <div className="page-shell">
    <div className="eyebrow">Platform administration</div><h1 className="page-title">Lawyer verification</h1>
    <p className="page-intro">Review pending lawyer profiles before they appear in the public marketplace.</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    {lawyers.isPending ? <div className="loading-state">Loading applications...</div> : lawyers.isError ? <div className="error-state" role="alert">Pending applications could not be loaded.</div> : (
      <div className="workflow-list">{lawyers.data?.length ? lawyers.data.map((lawyer) => (
        <article className="workflow-card" key={lawyer.user_id}>
          <div className="workflow-card-head"><div><h2>{lawyer.full_name}</h2><p>{lawyer.email}{lawyer.phone ? ` · ${lawyer.phone}` : ""}</p></div><span className="status-badge status-pending">{humanize(lawyer.verification_status)}</span></div>
          <div className="case-meta"><span>License {lawyer.license_number}</span><span>{lawyer.bar_council} · {lawyer.bar_council_number}</span></div>
          <div className="case-meta"><span>{lawyer.specialization ?? "Specialization not specified"}</span><span>{lawyer.city ?? "City not specified"}</span><span>{lawyer.years_of_experience} years&apos; experience</span></div>
          <div className="workflow-actions"><button className="button button-small" onClick={() => void review(lawyer.user_id, "approve")} type="button">Approve</button><button className="button button-small button-danger" onClick={() => void review(lawyer.user_id, "reject")} type="button">Reject</button></div>
        </article>
      )) : <div className="empty-state">No pending lawyer applications.</div>}</div>
    )}
  </div>;
}

export function AdminUsersPage() {
  const currentUser = useCurrentUser("admin");
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [requestError, setRequestError] = useState("");
  const users = useQuery({
    queryKey: ["admin-users", search],
    enabled: currentUser.data?.role === "admin",
    queryFn: async () => {
      const { data } = await api.get<AdminUser[]>("/admin/users", {
        params: { limit: 100, ...(search.trim() ? { search: search.trim() } : {}) },
      });
      return data;
    },
  });
  async function toggleActive(user: AdminUser) {
    setRequestError("");
    const action = user.is_active ? "deactivate" : "activate";
    try {
      await api.put(`/admin/users/${user.id}/${action}`);
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    } catch (cause) {
      setRequestError(getApiError(cause, `Could not ${action} this account.`));
    }
  }
  if (currentUser.isPending || !currentUser.data) return <div className="page-shell"><div className="loading-state">Loading users...</div></div>;
  if (currentUser.data.role !== "admin") return <div className="page-shell"><div className="loading-state">Redirecting to your workspace...</div></div>;
  return <div className="page-shell">
    <div className="eyebrow">Platform administration</div><h1 className="page-title">Users</h1>
    <p className="page-intro">Find accounts and manage access. Your own administrator account cannot be deactivated here.</p>
    <label className="field admin-search">Search by email or phone<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search users" /></label>
    {requestError && <p className="form-error" role="alert">{requestError}</p>}
    {users.isPending ? <div className="loading-state">Loading users...</div> : users.isError ? <div className="error-state" role="alert">User accounts could not be loaded.</div> : (
      <div className="workflow-list">{users.data?.length ? users.data.map((user) => (
        <article className="workflow-card user-row" key={user.id}>
          <div><h2>{user.email}</h2><p>{humanize(user.role)} · Account #{user.id}{user.phone ? ` · ${user.phone}` : ""}</p></div>
          <div className="workflow-actions"><span className={`status-badge ${user.is_active ? "status-approved" : "status-rejected"}`}>{user.is_active ? "Active" : "Inactive"}</span><button className="button button-small button-outline" disabled={user.id === currentUser.data.id} onClick={() => void toggleActive(user)} type="button">{user.is_active ? "Deactivate" : "Activate"}</button></div>
        </article>
      )) : <div className="empty-state">No users found.</div>}</div>
    )}
  </div>;
}

function Stat({ label, value }: { label: string; value: number }) {
  return <div className="detail-info"><small>{label}</small><strong>{value.toLocaleString()}</strong></div>;
}
