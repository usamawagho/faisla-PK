"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getApiError } from "@/lib/api";
import { useCurrentUser } from "@/features/shared/use-current-user";
import { formatDateTime } from "@/features/shared/format";
import type { Notification } from "@/types/workflows";
import { useState } from "react";

export function NotificationsPage() {
  const currentUser = useCurrentUser();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const notifications = useQuery({
    queryKey: ["notifications", currentUser.data?.id],
    enabled: Boolean(currentUser.data),
    queryFn: async () => (await api.get<Notification[]>("/notifications?limit=100")).data,
  });
  async function markRead(id: string) {
    setError("");
    try {
      await api.put(`/notifications/${id}/read`);
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    } catch (cause) {
      setError(getApiError(cause, "Could not mark this notification as read."));
    }
  }
  if (currentUser.isPending || !currentUser.data) return <div className="page-shell"><div className="loading-state">Loading notifications...</div></div>;
  const unread = notifications.data?.filter((item) => !item.is_read).length ?? 0;
  return (
    <div className="page-shell">
      <div className="eyebrow">Updates</div>
      <h1 className="page-title">Notifications</h1>
      <p className="page-intro">{unread ? `${unread} unread update${unread === 1 ? "" : "s"}.` : "You are all caught up."}</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      {notifications.isPending ? <div className="loading-state">Loading notifications...</div> : notifications.isError ? (
        <div className="error-state" role="alert">Notifications could not be loaded.</div>
      ) : (
        <div className="workflow-list">{notifications.data?.length ? notifications.data.map((item) => (
          <article className={`workflow-card notification-card ${item.is_read ? "notification-read" : ""}`} key={item.id}>
            <div className="workflow-card-head"><h2>{item.title}</h2><time>{formatDateTime(item.created_at)}</time></div>
            <p>{item.message}</p>
            {!item.is_read && <button className="button button-small button-outline" onClick={() => void markRead(item.id)} type="button">Mark as read</button>}
          </article>
        )) : <div className="empty-state">You have no notifications yet.</div>}</div>
      )}
    </div>
  );
}
