import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import {
  getBackendUrl,
  logBackendFailure,
  logBackendResponse,
} from "@/lib/backend-api";
import { isSameOrigin } from "@/lib/request-security";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  if (
    !["GET", "HEAD", "OPTIONS"].includes(request.method) &&
    !isSameOrigin(request)
  ) {
    return NextResponse.json({ detail: "Invalid request origin." }, { status: 403 });
  }

  const { path } = await context.params;
  if (
    !path.length ||
    path.some((part) => !/^[a-zA-Z0-9._-]+$/.test(part) || part === "." || part === "..")
  ) {
    return NextResponse.json({ detail: "Invalid API path." }, { status: 400 });
  }

  const cookieStore = await cookies();
  const accessToken = cookieStore.get("faisla_access")?.value;
  const refreshToken = cookieStore.get("faisla_refresh")?.value;
  const target = getBackendUrl(path.map((part) => encodeURIComponent(part)).join(""));
  target.search = request.nextUrl.search;
  const method = request.method;
  const body =
    method === "GET" || method === "HEAD"
      ? undefined
      : await request.arrayBuffer();
  const headers = new Headers({ Accept: "application/json" });
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body: body?.slice(0),
      cache: "no-store",
      redirect: "manual",
    });
  } catch (error) {
    logBackendFailure(`/api/backend/${path.join("/")}`, target, error);
    return NextResponse.json(
      { detail: "The Faisla API is unavailable. Try again shortly." },
      { status: 503 },
    );
  }
  logBackendResponse(`/api/backend/${path.join("/")}`, target, upstream.status);

  let refreshedAccess: string | undefined;
  let refreshedRefresh: string | undefined;
  if (upstream.status === 401 && refreshToken && path.join("/") !== "auth/refresh") {
    try {
      const refreshTarget = getBackendUrl("/auth/refresh");
      const refreshed = await fetch(refreshTarget, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
      logBackendResponse("/api/backend/auth/refresh", refreshTarget, refreshed.status);
      const tokens = (await refreshed.json().catch(() => null)) as
        | { access_token?: string; refresh_token?: string }
        | null;
      if (
        refreshed.ok &&
        tokens?.access_token &&
        tokens.refresh_token
      ) {
        refreshedAccess = tokens.access_token;
        refreshedRefresh = tokens.refresh_token;
        headers.set("Authorization", `Bearer ${refreshedAccess}`);
        upstream = await fetch(target, {
          method,
          headers,
          body: body?.slice(0),
          cache: "no-store",
          redirect: "manual",
        });
      }
    } catch (error) {
      logBackendFailure("/api/backend/auth/refresh", undefined, error);
      refreshedAccess = undefined;
    }
  }

  const responseHeaders = new Headers();
  for (const header of ["content-type", "content-disposition", "cache-control"]) {
    const value = upstream.headers.get(header);
    if (value) responseHeaders.set(header, value);
  }
  const response = new NextResponse(
    upstream.status === 204 ? null : await upstream.arrayBuffer(),
    { status: upstream.status, headers: responseHeaders },
  );
  if (refreshedAccess) {
    response.cookies.set("faisla_access", refreshedAccess, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 15 * 60,
    });
  }
  if (refreshedRefresh) {
    response.cookies.set("faisla_refresh", refreshedRefresh, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60,
    });
  }
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
