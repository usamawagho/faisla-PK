import { NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-security";

export async function POST(request: Request) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Invalid request origin." }, { status: 403 });
  }
  return register(request, "client");
}

async function register(request: Request, role: "client" | "lawyer") {
  const apiUrl = process.env.FAISLA_API_URL ?? "http://127.0.0.1:8000";
  let upstream: Response;
  try {
    upstream = await fetch(
      `${apiUrl.replace(/\/+$/, "")}/auth/register/${role}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await request.text(),
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      { detail: "The Faisla API is unavailable. Try again shortly." },
      { status: 503 },
    );
  }
  const body = await upstream.text();
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
