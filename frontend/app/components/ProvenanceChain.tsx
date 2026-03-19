'use client';
import { motion } from 'framer-motion';

interface ProvenanceEntry {
  agent_name: string;
  timestamp: string;
  input_summary: string;
  output_summary: string;
  tools_used: string[];
  confidence_score: number;
  duration_ms?: number;
}

export default function ProvenanceChain({ entries }: { entries: ProvenanceEntry[] }) {
  if (!entries.length) return (
    <div className="text-center py-12 text-slate-600 text-sm">
      No provenance data yet. Run a session to generate the audit trail.
    </div>
  );

  return (
    <div className="relative">
      {/* Timeline spine */}
      <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-indigo-500/40 via-purple-500/20 to-transparent" />

      <div className="space-y-6 ml-12">
        {entries.map((entry, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className="relative"
          >
            {/* Timeline dot */}
            <div className="absolute -left-[2.35rem] top-3 w-4 h-4 rounded-full border-2 border-indigo-500 bg-[#0f0f23] flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            </div>

            <div className="glass-card p-4">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                    {entry.agent_name.replace('_', ' ')} Agent
                  </span>
                  <div className="text-[11px] text-slate-500 mt-0.5 font-mono">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                    {entry.duration_ms && ` · ${(entry.duration_ms / 1000).toFixed(2)}s`}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="flex h-2 w-20 rounded-full overflow-hidden bg-slate-800">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${entry.confidence_score * 100}%` }}
                      transition={{ delay: i * 0.08 + 0.3, duration: 0.6 }}
                      className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full"
                    />
                  </div>
                  <span className="text-xs text-slate-400 font-mono w-9 text-right">
                    {Math.round(entry.confidence_score * 100)}%
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-slate-500 mb-1 font-medium">Input</div>
                  <div className="text-slate-300 leading-relaxed bg-black/20 p-2 rounded border border-white/5">
                    {entry.input_summary}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 mb-1 font-medium">Output</div>
                  <div className="text-slate-300 leading-relaxed bg-black/20 p-2 rounded border border-white/5">
                    {entry.output_summary}
                  </div>
                </div>
              </div>

              {entry.tools_used.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {entry.tools_used.map((t, i) => (
                    <span key={`${t}-${i}`} className="text-[10px] px-2 py-0.5 rounded bg-purple-900/30 text-purple-400 border border-purple-500/20 font-mono">
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
  );
}
