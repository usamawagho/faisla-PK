"use client";

import { type FormEvent, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, getApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { User } from "@/types/api";

export default function LoginPage({ adminOnly = false }: { adminOnly?: boolean }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const setUser = useAuthStore((state) => state.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Sign in failed.");
      }
      queryClient.clear();
      const { data: user } = await api.get<User>("/auth/me");
      if (adminOnly ? user.role !== "admin" : user.role === "admin") {
        await fetch("/api/auth/logout", { method: "POST" });
        queryClient.clear();
        setUser(null);
        throw new Error(
          adminOnly
            ? "This account does not have administrator access."
            : "Administrators should sign in through the administrator portal.",
        );
      }
      setUser(user);
      router.replace(
        user.role === "admin"
          ? "/admin/dashboard"
          : user.role === "lawyer"
            ? "/portal"
            : "/dashboard",
      );
      router.refresh();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : getApiError(submitError, "Sign in failed. Please try again."),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className={`auth-card login-card${adminOnly ? " admin-login-card" : ""}`}>
        <div className="eyebrow">{adminOnly ? "Faisla Administration" : "Welcome back"}</div>
        <h1>{adminOnly ? "Administrator sign in" : "Sign in to Faisla"}</h1>
        {adminOnly ? (
          <p className="auth-description">Authorized administrators only.</p>
        ) : (
          <>
            <p className="auth-description">Clients and Lawyers use the same secure login.</p>
            <div aria-label="Available portals" className="portal-badges">
              <span><span aria-hidden="true">◉</span> Client Portal</span>
              <span><span aria-hidden="true">⚖</span> Lawyer Portal</span>
            </div>
          </>
        )}
        <form className="form-stack" onSubmit={submit}>
          <div className="field">
            <label htmlFor="email">Email address</label>
            <input autoComplete="email" id="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input autoComplete="current-password" id="password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          </div>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="button auth-submit" disabled={submitting} type="submit">
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {!adminOnly && (
          <p className="auth-switch">New to Faisla? <Link href="/register">Create an account</Link></p>
        )}
      </section>
    </div>
  );
}
