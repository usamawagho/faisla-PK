import { NextRequest, NextResponse } from "next/server";
import {
  getBackendUrl,
  logBackendFailure,
  logBackendResponse,
} from "@/lib/backend-api";
import { isSameOrigin } from "@/lib/request-security";

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Invalid request origin." }, { status: 403 });
  }

  const refreshToken = request.cookies.get("faisla_refresh")?.value;
  let logoutFailed = false;
  if (refreshToken) {
    let target: URL | undefined;
    try {
      target = getBackendUrl("/auth/logout");
      const upstream = await fetch(target, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
      logBackendResponse("/api/auth/logout", target, upstream.status);
      logoutFailed = !upstream.ok && upstream.status !== 401;
    } catch (error) {
      logBackendFailure("/api/auth/logout", target, error);
      logoutFailed = true;
    }
  }

  const response = NextResponse.json(
    logoutFailed
      ? { authenticated: false, detail: "Could not revoke the server session." }
      : { authenticated: false },
    { status: logoutFailed ? 503 : 200 },
  );
  const cookieOptions = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: 0,
  };
  response.cookies.set("faisla_access", "", cookieOptions);
  response.cookies.set("faisla_refresh", "", cookieOptions);
  return response;
}
