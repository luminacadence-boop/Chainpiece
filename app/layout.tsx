import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chainpiece Chat",
  description: "Minimal chat interface powered by Mistral Small",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-neutral-950 text-neutral-100 antialiased">
        {children}
      </body>
    </html>
  );
}
