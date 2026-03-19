'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';

const NAV = [
  { href: '/',           label: 'Mission Control', icon: '⬡' },
  { href: '/sessions',   label: 'Sessions',         icon: '◈' },
  { href: '/knowledge',  label: 'Knowledge Base',   icon: '◉' },
  { href: '/tools',      label: 'Tool Connections', icon: '⚙' },
  { href: '/provenance', label: 'Provenance',        icon: '◎' },
  { href: '/docs',       label: 'Architecture',      icon: '◇' },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 flex flex-col bg-[#0a0a1a] border-r border-[#2a2a4a] z-40">
      {/* Logo */}
      <div className="px-6 py-6 border-b border-[#2a2a4a]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg nexus-glow">
            N
          </div>
          <div>
            <div className="font-bold text-white text-sm tracking-wide">NEXUS</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-widest">Agentic Platform</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="text-[10px] text-slate-600 uppercase tracking-widest px-3 mb-3 font-medium">
          Navigation
        </div>
        {NAV.map(({ href, label, icon }) => {
          const active = path === href;
          return (
            <Link key={href} href={href}>
              <motion.div
                whileHover={{ x: 3 }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                  active
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#1e1e38]'
                }`}
              >
                <span className={`text-base ${active ? 'text-indigo-400' : ''}`}>{icon}</span>
                {label}
                {active && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-400"
                  />
                )}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-[#2a2a4a] space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-slate-500">System Online</span>
        </div>
        <div className="text-[10px] text-slate-600">v1.0.0 · LangGraph 0.2</div>
        {/* Security status */}
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/20 px-3 py-2">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-emerald-400 text-[11px]">🔒</span>
            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Secured</span>
          </div>
          <div className="space-y-0.5">
            {['Rate limiting', 'Security headers', 'CSP enforced', 'Prompt guard'].map(f => (
              <div key={f} className="flex items-center gap-1.5 text-[9px] text-slate-500">
                <span className="text-emerald-500">✓</span>{f}
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
