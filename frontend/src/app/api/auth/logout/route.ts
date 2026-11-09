import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-security";

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Invalid request origin." }, { status: 403 });
  }

  const refreshToken = request.cookies.get("faisla_refresh")?.value;
  let logoutFailed = false;
  if (refreshToken) {
    try {
      const apiUrl = (process.env.FAISLA_API_URL ?? "http://127.0.0.1:8000").replace(
        /\/+$/,
        "",
      );
      const upstream = await fetch(`${apiUrl}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
      logoutFailed = !upstream.ok && upstream.status !== 401;
    } catch {
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
