'use client';
import { motion, AnimatePresence } from 'framer-motion';

export type AgentStatus = 'idle' | 'running' | 'complete' | 'error';

export interface AgentStep {
  id: string;
  label: string;
  subtitle: string;
  icon: string;
  status: AgentStatus;
  duration_ms?: number;
  confidence?: number;
  tools_used?: string[];
  output_summary?: string;
}

const STATUS_COLORS: Record<AgentStatus, string> = {
  idle:     'border-[#2a2a4a] bg-[#16162a] text-slate-500',
  running:  'border-indigo-500/60 bg-indigo-950/40 text-indigo-300 nexus-glow',
  complete: 'border-emerald-500/40 bg-emerald-950/30 text-emerald-300',
  error:    'border-red-500/40 bg-red-950/30 text-red-300',
};

const STATUS_DOTS: Record<AgentStatus, string> = {
  idle:     'bg-slate-600',
  running:  'bg-indigo-400 animate-pulse',
  complete: 'bg-emerald-400',
  error:    'bg-red-400',
};

export default function AgentPipeline({ steps }: { steps: AgentStep[] }) {
  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <div key={step.id} className="relative">
          {/* Connector line */}
          {i < steps.length - 1 && (
            <div className="absolute left-[23px] top-[52px] w-0.5 h-3 bg-gradient-to-b from-[#2a2a4a] to-transparent z-0" />
          )}

          <motion.div
            layout
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`relative flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${STATUS_COLORS[step.status]}`}
          >
            {/* Icon + status dot */}
            <div className="relative flex-shrink-0 mt-0.5">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl
                ${step.status === 'running' ? 'bg-indigo-600/30 agent-pulse' :
                  step.status === 'complete' ? 'bg-emerald-600/20' :
                  step.status === 'error' ? 'bg-red-600/20' : 'bg-[#1e1e38]'}`}>
                {step.icon}
              </div>
              <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#0f0f23] ${STATUS_DOTS[step.status]}`} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="font-semibold text-sm">{step.label}</div>
                  <div className="text-xs opacity-60 mt-0.5">{step.subtitle}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {step.confidence !== undefined && step.status === 'complete' && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-900/40 text-emerald-400 border border-emerald-500/20">
                      {Math.round(step.confidence * 100)}%
                    </span>
                  )}
                  {step.duration_ms !== undefined && (
                    <span className="text-xs text-slate-500 font-mono">
                      {step.duration_ms < 1000
                        ? `${Math.round(step.duration_ms)}ms`
                        : `${(step.duration_ms / 1000).toFixed(1)}s`}
                    </span>
                  )}
                  {step.status === 'running' && (
                    <div className="flex gap-1">
                      {[0,1,2].map(j => (
                        <motion.div
                          key={j}
                          className="w-1 h-1 rounded-full bg-indigo-400"
                          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
                          transition={{ duration: 1.2, repeat: Infinity, delay: j * 0.2 }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Output summary */}
              <AnimatePresence>
                {step.output_summary && step.status === 'complete' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-2 text-xs text-slate-400 leading-relaxed bg-black/20 rounded-lg px-3 py-2 font-mono border border-white/5"
                  >
                    {step.output_summary}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Tools used */}
              {step.tools_used && step.tools_used.length > 0 && step.status === 'complete' && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {step.tools_used.map(t => (
                    <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-[#1e1e38] text-slate-400 border border-[#2a2a4a] font-mono">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      ))}
    </div>
  );
}
