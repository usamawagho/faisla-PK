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
  return register(request, "client");
}

async function register(request: Request, role: "client" | "lawyer") {
  let target: URL | undefined;
  let upstream: Response;
  try {
    target = getBackendUrl(`/auth/register/${role}`);
    upstream = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
  } catch (error) {
    logBackendFailure(`/api/auth/register/${role}`, target, error);
    return NextResponse.json(
      { detail: "The Faisla API is unavailable. Try again shortly." },
      { status: 503 },
    );
  }
  logBackendResponse(`/api/auth/register/${role}`, target, upstream.status);
  const body = await upstream.text();
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
