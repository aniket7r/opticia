import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "gemini3 - See the World Differently",
  description: "Real-time visual understanding AI with voice guidance",
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
