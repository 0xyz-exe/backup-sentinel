import "./globals.css";
import React from "react";

export const metadata = {
  title: "Backup Sentinel — Automated Verification & Recovery Testing",
  description: "Self-hosted backup verification, recovery testing, and RTO/RPO compliance monitoring platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased">{children}</body>
    </html>
  );
}
