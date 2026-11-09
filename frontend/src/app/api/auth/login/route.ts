import { NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-security";

const apiUrl = process.env.FAISLA_API_URL ?? "http://127.0.0.1:8000";

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

  let upstream: Response;
  try {
    upstream = await fetch(`${apiUrl.replace(/\/+$/, "")}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "The Faisla API is unavailable. Try again shortly." },
      { status: 503 },
    );
  }

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
