import type { Metadata } from "next";
import type { ReactNode } from "react";
import { QueryProvider } from "@/components/query-provider";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Faisla PK — Find the right legal help",
    template: "%s | Faisla PK",
  },
  description:
    "Discover verified lawyers, manage appointments, and keep your legal matters organized with Faisla PK.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <SiteHeader />
          <main>{children}</main>
          <footer className="site-footer">
            <div className="footer-inner">
              <span className="footer-brand">faisla.pk</span>
              <span>Legal support, made more accessible.</span>
              <span>© {new Date().getFullYear()} Faisla PK</span>
            </div>
          </footer>
        </QueryProvider>
      </body>
    </html>
  );
}
