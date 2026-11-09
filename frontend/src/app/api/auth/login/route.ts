import { NextResponse } from "next/server";
import {
  getBackendUrl,
  logBackendFailure,
  logBackendResponse,
} from "@/lib/backend-api";
import { isSameOrigin } from "@/lib/request-security";

export async function POST(request: Request) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Invalid request origin." }, { status: 403 });
  }

  let credentials: { email?: unknown; password?: unknown };
  try {
    credentials = (await request.json()) as typeof credentials;
  } catch {
    return NextResponse.json({ detail: "Invalid sign-in request." }, { status: 400 });
  }
  if (
    typeof credentials.email !== "string" ||
    typeof credentials.password !== "string" ||
    !credentials.email.trim() ||
    !credentials.password
  ) {
    return NextResponse.json(
      { detail: "Enter your email and password." },
      { status: 422 },
    );
  }

  const form = new URLSearchParams({
    username: credentials.email.trim().toLowerCase(),
    password: credentials.password,
  });

  let target: URL | undefined;
  let upstream: Response;
  try {
    target = getBackendUrl("/auth/login");
    upstream = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
      cache: "no-store",
    });
  } catch (error) {
    logBackendFailure("/api/auth/login", target, error);
    return NextResponse.json(
      { detail: "The Faisla API is unavailable. Try again shortly." },
      { status: 503 },
    );
  }
  logBackendResponse("/api/auth/login", target, upstream.status);

  const payload = (await upstream.json().catch(() => null)) as
    | { access_token?: string; refresh_token?: string; detail?: string }
    | null;
  if (
    !upstream.ok ||
    typeof payload?.access_token !== "string" ||
    typeof payload.refresh_token !== "string"
  ) {
    return NextResponse.json(
      { detail: payload?.detail ?? "Sign in failed." },
      { status: upstream.ok ? 502 : upstream.status },
    );
  }

  const response = NextResponse.json({ authenticated: true });
  const secure = process.env.NODE_ENV === "production";
  response.cookies.set("faisla_access", payload.access_token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60,
  });
  response.cookies.set("faisla_refresh", payload.refresh_token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 60 * 60,
  });
  return response;
}
