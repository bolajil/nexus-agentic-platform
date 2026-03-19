'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Sidebar from '../components/Sidebar';

interface SessionSummary {
  id: string;
  name: string;
  status: string;
  created_at: string;
  domain?: string;
  brief_excerpt: string;
}

const STATUS_BADGE: Record<string, string> = {
  complete: 'bg-emerald-900/30 text-emerald-400 border-emerald-500/20',
  running:  'bg-indigo-900/30 text-indigo-400 border-indigo-500/20',
  pending:  'bg-slate-800 text-slate-400 border-slate-600/20',
  error:    'bg-red-900/30 text-red-400 border-red-500/20',
};

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then(data => setSessions(Array.isArray(data) ? data : []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Sessions</h1>
          <p className="text-slate-400 mt-1 text-sm">All engineering pipeline runs with full provenance</p>
        </div>

        {loading ? (
          <div className="flex items-center gap-3 text-slate-500">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full"
            />
            Loading sessions…
          </div>
        ) : sessions.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <div className="text-4xl mb-4">◈</div>
            <div className="text-slate-400 mb-4">No sessions yet</div>
            <Link href="/" className="text-indigo-400 hover:text-indigo-300 text-sm">
              Launch your first pipeline →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((s, i) => (
              <motion.div
                key={s.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <Link href={`/sessions/${s.id}`}>
                  <div className="glass-card p-5 hover:border-indigo-500/30 hover:bg-indigo-950/10 transition-all cursor-pointer group">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="font-semibold text-white group-hover:text-indigo-300 transition-colors">
                            {s.name}
                          </span>
                          {s.domain && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-900/30 text-purple-400 border border-purple-500/20 uppercase tracking-wider">
                              {s.domain.replace('_', ' ')}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-500 line-clamp-2 font-mono leading-relaxed">
                          {s.brief_excerpt}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2 flex-shrink-0">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium uppercase tracking-wider ${STATUS_BADGE[s.status] || STATUS_BADGE.pending}`}>
                          {s.status}
                        </span>
                        <span className="text-[11px] text-slate-600 font-mono">
                          {new Date(s.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
