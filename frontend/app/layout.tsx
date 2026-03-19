import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'NEXUS — Multi-Agent Engineering Platform',
  description: 'Production-grade agentic AI platform for autonomous hardware design. Routes engineering briefs through a 6-agent LangGraph pipeline.',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0f0f23] text-slate-100 antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
