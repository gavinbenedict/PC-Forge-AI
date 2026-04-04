/**
 * PCForge AI v2 — Global Layout
 */
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "PCForge AI v2 — Intelligent PC Build Pricing Engine",
  description:
    "Dataset-driven AI PC build analyser. Validate compatibility, get real-time pricing, intelligent component recommendations, and export full build reports with ML price prediction.",
  keywords: "PC builder, GPU pricing, CPU compatibility, PC build tool, AI PC configurator, PCForge",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap"
          rel="stylesheet"
        />
        <link
          rel="icon"
          href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>"
        />
      </head>
      <body>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
