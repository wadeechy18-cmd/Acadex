import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Acadex — Learn. Practice. Ask. Improve.",
  description:
    "A free education platform for GCSE, International A-Level, and first-year university Computer Science students.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
