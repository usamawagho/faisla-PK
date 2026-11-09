export class BackendConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BackendConfigurationError";
  }
}

export function getBackendUrl(path: string): URL {
  const configuredUrl = process.env.FAISLA_API_URL?.trim();
  if (!configuredUrl && process.env.NODE_ENV === "production") {
    throw new BackendConfigurationError(
      "FAISLA_API_URL must be configured for production.",
    );
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(configuredUrl || "http://127.0.0.1:8000");
  } catch {
    throw new BackendConfigurationError("FAISLA_API_URL is not a valid URL.");
  }
  if (
    !["http:", "https:"].includes(baseUrl.protocol) ||
    baseUrl.username ||
    baseUrl.password
  ) {
    throw new BackendConfigurationError(
      "FAISLA_API_URL must be an HTTP(S) URL without embedded credentials.",
    );
  }

  const prefix = baseUrl.pathname.replace(/\/+$/, "");
  const suffix = path.replace(/^\/+/, "");
  return new URL(`${prefix}/${suffix}`, baseUrl.origin);
}

function safeTarget(target?: URL): string {
  return target ? `${target.origin}${target.pathname}` : "unresolved";
}

export function logBackendResponse(
  route: string,
  target: URL,
  status: number,
): void {
  console.info(
    `[backend-proxy] route=${route} target=${safeTarget(target)} status=${status}`,
  );
}

export function logBackendFailure(
  route: string,
  target: URL | undefined,
  error: unknown,
): void {
  const errorType = error instanceof Error ? error.name : "UnknownError";
  console.error(
    `[backend-proxy] route=${route} target=${safeTarget(target)} error=${errorType}`,
  );
}
