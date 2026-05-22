import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SimAB — UX Pretest",
  description: "Simulate audience response to landing-page variants",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-50 text-neutral-900 antialiased">
        <header className="border-b border-neutral-200 bg-white">
          <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
            <a href="/" className="font-semibold tracking-tight">SimAB</a>
            <a
              href="/new"
              className="text-sm px-3 py-1.5 rounded-md bg-neutral-900 text-white hover:bg-neutral-700"
            >
              New run
            </a>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
