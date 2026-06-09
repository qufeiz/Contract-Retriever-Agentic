import type { Metadata } from "next";
import { Fraunces, Newsreader, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Distinctive editorial pairing — a characterful display serif + a document-native
// reading serif + a ledger monospace for citations/data. (Not Inter/Roboto.)
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  axes: ["opsz", "SOFT", "WONK"],
  // weight omitted → full variable range (axes require variable weight)
});
const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});
const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "Aletheia — AI Business Knowledge Assistant",
  description:
    "Ask a business question — routed to the right source(s), answered with hybrid SQL + RAG retrieval and inline citations you can trace.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${newsreader.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
