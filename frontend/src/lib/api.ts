import axios from "axios";
import type { ApiError } from "@/types/api";

export const api = axios.create({
  baseURL: "/api/backend",
  headers: { Accept: "application/json" },
  withCredentials: true,
});

export function getApiError(error: unknown, fallback: string): string {
  if (axios.isAxiosError<ApiError>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => item.msg)
        .filter((message): message is string => Boolean(message));
      if (messages.length) return messages.join(" ");
    }
  }
  return fallback;
}
