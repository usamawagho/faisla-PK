"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { User, UserRole } from "@/types/api";

function roleHome(role: UserRole) {
  if (role === "admin") return "/admin/dashboard";
  if (role === "lawyer") return "/portal";
  return "/dashboard";
}

export function useCurrentUser(requiredRole?: UserRole) {
  const router = useRouter();
  const setUser = useAuthStore((state) => state.setUser);
  const query = useQuery({
    queryKey: ["current-user"],
    queryFn: async () => {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
      return data;
    },
    retry: false,
  });

  useEffect(() => {
    if (query.isError) router.replace("/login");
  }, [query.isError, router]);

  useEffect(() => {
    if (query.data && requiredRole && query.data.role !== requiredRole) {
      router.replace(roleHome(query.data.role));
    }
  }, [query.data, requiredRole, router]);

  return query;
}
