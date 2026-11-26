import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Porto Resiliente",
  description: "Alertas de cheias, calor, vento e qualidade do ar por zona do Porto.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-PT">
      <body>{children}</body>
    </html>
  );
}
