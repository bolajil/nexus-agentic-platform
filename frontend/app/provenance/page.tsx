'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';

interface SessionSummary {
  id: string;
  name: string;
  status: string;
  provenance_chain?: unknown[];
}

export default function ProvenancePage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data.filter((s: SessionSummary) => s.status === 'complete') : [];
        setSessions(list);
        if (list.length > 0) setSelected(list[0].id);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetch(`/api/sessions/${selected}`)
      .then(r => r.json())
      .then(s => setProvenance(s?.provenance_chain || []));
  }, [selected]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Provenance & Audit Trail</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Every agent decision is recorded — input, output, tools used, confidence, and duration
          </p>
        </div>

        {loading ? (
          <div className="text-slate-500">Loading…</div>
        ) : sessions.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500">
            Run a complete pipeline session to see provenance data here.
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            {/* Session list */}
            <div className="xl:col-span-1 space-y-2">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Completed Sessions</div>
              {sessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => setSelected(s.id)}
                  className={`w-full text-left p-3 rounded-lg border text-sm transition-all ${
                    selected === s.id
                      ? 'bg-indigo-900/30 border-indigo-500/40 text-indigo-300'
                      : 'bg-[#16162a] border-[#2a2a4a] text-slate-400 hover:border-indigo-500/20 hover:text-slate-200'
                  }`}
                >
                  <div className="font-medium text-xs">{s.name}</div>
                  <div className="text-[10px] opacity-60 font-mono mt-0.5">{s.id.slice(0, 12)}…</div>
                </button>
              ))}
            </div>

            {/* Provenance chain */}
            <div className="xl:col-span-3">
              {provenance.length === 0 ? (
                <div className="text-slate-600 text-center py-12">Select a session to view its provenance chain</div>
              ) : (
                <div className="relative">
                  <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-indigo-500/40 via-purple-500/20 to-transparent" />
                  <div className="space-y-5 ml-12">
                    {(provenance as Array<{
                      agent_name: string;
                      timestamp: string;
                      input_summary: string;
                      output_summary: string;
                      tools_used: string[];
                      confidence_score: number;
                      duration_ms?: number;
                    }>).map((entry, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -12 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="relative"
                      >
                        <div className="absolute -left-[2.35rem] top-4 w-4 h-4 rounded-full border-2 border-indigo-500 bg-[#0f0f23] flex items-center justify-center">
                          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                        </div>
                        <div className="glass-card p-5">
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                                {String(entry.agent_name).replace('_', ' ')} Agent
                              </span>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {new Date(entry.timestamp).toLocaleTimeString()}
                                {entry.duration_ms && ` · ${(entry.duration_ms / 1000).toFixed(2)}s`}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 w-16 rounded-full overflow-hidden bg-slate-800">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{ width: `${entry.confidence_score * 100}%` }}
                                  transition={{ delay: i * 0.08 + 0.3, duration: 0.6 }}
                                  className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500"
                                />
                              </div>
                              <span className="text-xs text-slate-400 font-mono">
                                {Math.round(entry.confidence_score * 100)}%
                              </span>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3 text-xs mb-3">
                            <div>
                              <div className="text-slate-600 mb-1">Input</div>
                              <div className="text-slate-300 bg-black/20 p-2 rounded border border-white/5 leading-relaxed">
                                {entry.input_summary}
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-600 mb-1">Output</div>
                              <div className="text-slate-300 bg-black/20 p-2 rounded border border-white/5 leading-relaxed">
                                {entry.output_summary}
                              </div>
                            </div>
                          </div>
                          {entry.tools_used?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {entry.tools_used.map((t: string) => (
                                <span key={t} className="text-[10px] px-2 py-0.5 rounded bg-purple-900/20 text-purple-400 border border-purple-500/20 font-mono">
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
