import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CORDA Deliberation",
  description: "Massively scalable deliberation via Telegram discussion groups.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
