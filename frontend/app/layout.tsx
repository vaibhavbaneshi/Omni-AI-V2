import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Omni AI - Your Intelligent Operating System",
  description: "The most powerful AI workspace for developers and teams. Chat, code, analyze documents, and build with AI.",
  keywords: ["AI", "ChatGPT", "Developer Tools", "AI Assistant", "Code Generation", "Document Analysis"],
  authors: [{ name: "Omni AI" }],
  openGraph: {
    title: "Omni AI - Your Intelligent Operating System",
    description: "The most powerful AI workspace for developers and teams.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0f0f12",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background">
        <TooltipProvider delayDuration={300}>
          {children}
        </TooltipProvider>
      </body>
    </html>
  );
}
