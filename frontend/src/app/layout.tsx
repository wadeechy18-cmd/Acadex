import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Acadex — Smarter Teaching. Better Planning. Less Admin.",
  description:
    "Acadex helps teachers create high-quality lesson plans aligned with the English National Curriculum, while helping schools manage teachers, classes, lesson planning and timetable changes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
