import type { ReactNode } from "react";
import { AdminShell } from "@/features/admin/admin-shell";

export default function Layout({ children }: Readonly<{ children: ReactNode }>) {
  return <AdminShell>{children}</AdminShell>;
}
