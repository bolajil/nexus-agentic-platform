'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from './components/Sidebar';
import AnoAI from '@/components/ui/animated-shader-background';
import AgentPipeline, { AgentStep, AgentStatus } from './components/AgentPipeline';
import DesignDiagram from './components/DesignDiagram';
import ShareModal from './components/ShareModal';
import ReviewPanel from './components/ReviewPanel';

const AGENT_META: Record<string, { label: string; subtitle: string; icon: string }> = {
  requirements: { label: 'Requirements Engineer', subtitle: 'Parses brief → domain, constraints, targets', icon: '📋' },
  research:     { label: 'Research Scientist',    subtitle: 'Semantic search over knowledge base',     icon: '🔬' },
  design:       { label: 'Design Engineer',       subtitle: 'Calculates parameters using physics',     icon: '📐' },
  simulation:   { label: 'Physics Simulator',     subtitle: 'Runs domain-specific simulation',         icon: '⚡' },
  optimization: { label: 'Optimization Engineer', subtitle: 'Pareto-optimal multi-objective search',   icon: '🎯' },
  report:       { label: 'Technical Writer',      subtitle: 'Compiles full engineering report',        icon: '📄' },
};

const EXAMPLE_BRIEFS = [
  'Design a heat sink for a 100W power module. Operating environment: 25°C ambient, forced air at 3 m/s. Maximum component temperature: 85°C. Material preference: aluminum. Target thermal resistance < 0.6 °C/W.',
  'Design a cold gas thruster for a 3U CubeSat attitude control system. Required thrust: 50 mN. Propellant: nitrogen. Available pressure: 300 bar. Target delta-v: 10 m/s.',
  'Structural analysis of an aluminum 6061-T6 bracket subjected to 500N axial load and 50 N·m bending moment. Factor of safety target: 2.5. Minimize mass.',
  'Design a de Laval convergent-divergent nozzle for a liquid bipropellant rocket engine. Chamber pressure: 5 MPa. Propellant: LOX/RP-1 with O/F ratio 2.5. Target sea-level thrust: 2000 N. Expansion ratio: 10:1. Chamber temperature: 3500 K. Optimize for maximum specific impulse (Isp > 280 s).',
];

const AGENT_ORDER = ['requirements', 'research', 'design', 'simulation', 'optimization', 'report'];

function makeSteps(): AgentStep[] {
  return AGENT_ORDER.map(id => ({
    id,
    ...AGENT_META[id],
    status: 'idle' as AgentStatus,
  }));
}

export default function MissionControl() {
  const [brief, setBrief] = useState('');
  const [sessionName, setSessionName] = useState('');
  const [steps, setSteps] = useState<AgentStep[]>(makeSteps());
  const [running, setRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [report, setReport] = useState<Record<string, string> | null>(null);
  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<string[]>([]);
  const [showShare, setShowShare] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const userIdRef = useRef<string>('');

  // Persist a stable user ID across sessions for Langfuse user tracking
  useEffect(() => {
    let uid = localStorage.getItem('nexus_user_id');
    if (!uid) {
      uid = 'user-' + crypto.randomUUID();
      localStorage.setItem('nexus_user_id', uid);
    }
    userIdRef.current = uid;
  }, []);

  const updateStep = useCallback((agentId: string, patch: Partial<AgentStep>) => {
    setSteps(prev => prev.map(s => s.id === agentId ? { ...s, ...patch } : s));
  }, []);

  const submitFeedback = async (type: 'up' | 'down') => {
    if (!sessionId || feedbackSubmitting) return;
    setFeedbackSubmitting(true);
    try {
      const endpoint = type === 'up' ? 'thumbs-up' : 'thumbs-down';
      await fetch(`/api/feedback/${endpoint}/${sessionId}?user_id=${userIdRef.current}`, {
        method: 'POST',
      });
      setFeedback(type);
    } catch (err) {
      console.error('Feedback failed:', err);
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const run = async () => {
    if (!brief.trim() || running) return;

    // Reset state
    setSteps(makeSteps());
    setReport(null);
    setSessionData(null);
    setEvents([]);
    setRunning(true);
    setSessionId(null);
    setFeedback(null);

    abortRef.current = new AbortController();

    try {
      const token = localStorage.getItem('nexus_access_token');
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userIdRef.current ? { 'X-User-ID': userIdRef.current } : {}),
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          engineering_brief: brief,
          session_name: sessionName || undefined,
        }),
        signal: abortRef.current.signal,
      });

      const sid = res.headers.get('X-Session-ID') || null;
      setSessionId(sid);

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '));

        for (const line of lines) {
          try {
            const event = JSON.parse(line.slice(6));
            const { type, agent, content } = event;

            setEvents(prev => [...prev.slice(-49), `[${type}] ${agent || ''} ${
              typeof content === 'string' ? content.slice(0, 80) :
              content?.output_summary?.slice(0, 80) || ''
            }`]);

            if (type === 'agent_start' && agent) {
              updateStep(agent, { status: 'running' });
            }

            if (type === 'agent_complete' && agent) {
              updateStep(agent, {
                status: 'complete',
                confidence:     content?.confidence_score,
                duration_ms:    content?.duration_ms,
                tools_used:     content?.tools_used || [],
                output_summary: content?.output_summary,
              });
            }

            if (type === 'error') {
              const currentRunning = agent ||
                steps.find(s => s.status === 'running')?.id;
              if (currentRunning) updateStep(currentRunning, { status: 'error' });
            }

            if (type === 'session_complete' && content?.status === 'complete') {
              const sdata = await fetch(`/api/sessions/${event.session_id || sid}`).then(r => r.json());
              if (sdata?.report) setReport(sdata.report);
              if (sdata) setSessionData(sdata);
            }
          } catch {}
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setEvents(prev => [...prev, `[error] ${err.message}`]);
      }
    } finally {
      setRunning(false);
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
    setRunning(false);
    setSteps(prev => prev.map(s => s.status === 'running' ? { ...s, status: 'error' } : s));
  };

  const allComplete = steps.every(s => s.status === 'complete');

  return (
    <div className="flex min-h-screen">
      {/* Animated shader background */}
      <div className="fixed inset-0 z-0">
        <AnoAI />
      </div>
      <div className="fixed inset-0 z-0 bg-black/60" />

      <Sidebar />

      <main className="relative z-10 ml-60 flex-1 p-8 max-w-[1400px]">
        {/* Header */}
        <div className="mb-8">
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-bold text-white nexus-glow-text"
          >
            Mission Control
          </motion.h1>
          <p className="text-slate-400 mt-1 text-sm">
            Submit an engineering brief to launch the 6-agent autonomous design pipeline
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {/* ── Left: Input + Pipeline ─────────────────────────────── */}
          <div className="space-y-6">
            {/* Brief input */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-6"
            >
              <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                <span className="w-5 h-5 rounded bg-indigo-600/30 flex items-center justify-center text-indigo-400 text-xs">1</span>
                Engineering Brief
              </h2>

              <input
                type="text"
                placeholder="Session name (optional)"
                value={sessionName}
                onChange={e => setSessionName(e.target.value)}
                className="w-full mb-3 px-4 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 placeholder-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition-colors"
              />

              <textarea
                rows={6}
                placeholder="Describe your engineering challenge in detail. Include domain, performance targets, constraints, and materials..."
                value={brief}
                onChange={e => setBrief(e.target.value)}
                disabled={running}
                className="w-full px-4 py-3 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 placeholder-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition-colors resize-none font-mono leading-relaxed"
              />

              {/* Example briefs */}
              <div className="mt-3 space-y-1.5">
                <div className="text-[11px] text-slate-600 uppercase tracking-wider mb-2">Examples</div>
                {EXAMPLE_BRIEFS.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => setBrief(ex)}
                    className="w-full text-left text-xs text-slate-500 hover:text-slate-300 px-3 py-2 rounded-lg hover:bg-[#1e1e38] border border-transparent hover:border-[#2a2a4a] transition-all line-clamp-2"
                  >
                    <span className="text-indigo-600 mr-2">#{i + 1}</span>{ex.slice(0, 90)}…
                  </button>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 mt-5">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={run}
                  disabled={!brief.trim() || running}
                  className="flex-1 py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-indigo-600 to-purple-600 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:from-indigo-500 hover:to-purple-500 transition-all nexus-glow"
                >
                  {running ? (
                    <span className="flex items-center justify-center gap-2">
                      <motion.span
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                      />
                      Pipeline Running…
                    </span>
                  ) : '⬡ Launch Pipeline'}
                </motion.button>

                {running && (
                  <button
                    onClick={cancel}
                    className="px-4 py-3 rounded-xl border border-red-500/30 text-red-400 hover:bg-red-900/20 text-sm transition-colors"
                  >
                    Abort
                  </button>
                )}
              </div>

              {sessionId && (
                <div className="mt-3 text-[11px] text-slate-600 font-mono">
                  Session: <span className="text-indigo-400">{sessionId}</span>
                </div>
              )}
            </motion.div>

            {/* Agent Pipeline */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card p-6"
            >
              <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                <span className="w-5 h-5 rounded bg-indigo-600/30 flex items-center justify-center text-indigo-400 text-xs">2</span>
                Agent Pipeline
                {allComplete && (
                  <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-emerald-900/30 text-emerald-400 border border-emerald-500/20">
                    Complete
                  </span>
                )}
              </h2>
              <AgentPipeline steps={steps} />
            </motion.div>
          </div>

          {/* ── Right: Event stream + Report ──────────────────────── */}
          <div className="space-y-6">
            {/* Live event log */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="glass-card p-6"
            >
              <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                <span className="w-5 h-5 rounded bg-indigo-600/30 flex items-center justify-center text-indigo-400 text-xs">3</span>
                SSE Event Stream
                {running && <div className="ml-auto w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />}
              </h2>
              <div className="h-56 overflow-y-auto space-y-1 font-mono text-[11px]">
                {events.length === 0 ? (
                  <div className="text-slate-700 text-center py-8">
                    Waiting for pipeline events…
                  </div>
                ) : (
                  events.map((e, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="stream-enter text-slate-400 leading-relaxed py-0.5 border-b border-[#1a1a30] last:border-0"
                    >
                      <span className="text-slate-600">{String(i + 1).padStart(3, '0')} </span>
                      {e}
                    </motion.div>
                  ))
                )}
              </div>
            </motion.div>

            {/* Engineering Report */}
            <AnimatePresence>
              {report && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.97 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="glass-card p-6"
                >
                  <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <span className="w-5 h-5 rounded bg-emerald-600/30 flex items-center justify-center text-emerald-400 text-xs">✓</span>
                    Engineering Report
                    <span className="ml-auto text-[10px] px-2 py-0.5 rounded bg-emerald-900/30 text-emerald-400 border border-emerald-500/20">
                      Generated
                    </span>
                  </h2>

                  <h3 className="text-lg font-bold text-white mb-2">{report.title}</h3>

                  <div className="space-y-4 text-sm text-slate-300">
                    {[
                      ['Executive Summary',   report.executive_summary],
                      ['Design Solution',     report.design_solution],
                      ['Simulation Results',  report.simulation_results],
                      ['Optimization',        report.optimization_results],
                      ['Conclusions',         report.conclusions],
                    ].map(([title, content]) => content && (
                      <div key={title as string}>
                        <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">{title}</div>
                        <div className="text-slate-400 leading-relaxed text-xs bg-black/20 p-3 rounded-lg border border-white/5">
                          {content}
                        </div>
                      </div>
                    ))}

                    {report.recommendations && Array.isArray(report.recommendations) && (
                      <div>
                        <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">Recommendations</div>
                        <ul className="space-y-1">
                          {(report.recommendations as unknown as string[]).map((r, i) => (
                            <li key={i} className="flex gap-2 text-xs text-slate-400">
                              <span className="text-indigo-500 flex-shrink-0">→</span>
                              {r}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-3 mt-4 flex-wrap">
                    <button
                      onClick={() => {
                        const el = document.createElement('a');
                        el.href = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(report, null, 2))}`;
                        el.download = `nexus-report-${Date.now()}.json`;
                        el.click();
                      }}
                      className="text-xs px-4 py-2 rounded-lg border border-indigo-500/30 text-indigo-400 hover:bg-indigo-900/20 transition-colors"
                    >
                      ↓ Export JSON
                    </button>
                    <button
                      onClick={() => setShowShare(true)}
                      className="text-xs px-4 py-2 rounded-lg border border-purple-500/30 text-purple-400 hover:bg-purple-900/20 transition-colors"
                    >
                      ↗ Share for Review
                    </button>
                    
                    {/* Thumbs Up/Down Feedback */}
                    <div className="flex gap-2 ml-auto">
                      <button
                        onClick={() => submitFeedback('up')}
                        disabled={feedbackSubmitting || feedback !== null}
                        className={`text-xl px-3 py-1.5 rounded-lg border transition-all ${
                          feedback === 'up'
                            ? 'border-emerald-500 bg-emerald-900/30 text-emerald-400'
                            : feedback === 'down'
                            ? 'border-slate-700 text-slate-600 cursor-not-allowed'
                            : 'border-slate-600 text-slate-400 hover:border-emerald-500/50 hover:text-emerald-400 hover:bg-emerald-900/20'
                        }`}
                        title="This was helpful"
                      >
                        👍
                      </button>
                      <button
                        onClick={() => submitFeedback('down')}
                        disabled={feedbackSubmitting || feedback !== null}
                        className={`text-xl px-3 py-1.5 rounded-lg border transition-all ${
                          feedback === 'down'
                            ? 'border-red-500 bg-red-900/30 text-red-400'
                            : feedback === 'up'
                            ? 'border-slate-700 text-slate-600 cursor-not-allowed'
                            : 'border-slate-600 text-slate-400 hover:border-red-500/50 hover:text-red-400 hover:bg-red-900/20'
                        }`}
                        title="This needs improvement"
                      >
                        👎
                      </button>
                      {feedback && (
                        <span className="text-[10px] text-slate-500 self-center ml-1">
                          Thanks for your feedback!
                        </span>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Design Diagram — appears after pipeline completes */}
            <AnimatePresence>
              {sessionData && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <DesignDiagram
                    domain={(sessionData.requirements as Record<string, unknown>)?.domain as string}
                    designParams={sessionData.design_params as Record<string, unknown>}
                    simResults={sessionData.simulation_results as Record<string, unknown>}
                    optimizedParams={sessionData.optimized_params as Record<string, unknown>}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Team Review Panel — appears once pipeline is complete */}
            <AnimatePresence>
              {sessionId && !running && (
                <ReviewPanel sessionId={sessionId} />
              )}
            </AnimatePresence>

            {/* Architecture info card */}
            {!running && !report && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="glass-card p-6"
              >
                <h2 className="text-sm font-semibold text-slate-400 mb-4">Platform Architecture</h2>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  {[
                    { label: 'Orchestration',  value: 'LangGraph StateGraph',   color: 'text-indigo-400' },
                    { label: 'LLM',            value: 'GPT-4o + GPT-4o-mini',  color: 'text-purple-400' },
                    { label: 'Knowledge Base', value: 'ChromaDB + RAG',         color: 'text-blue-400'   },
                    { label: 'Session Store',  value: 'Redis / In-Memory',      color: 'text-cyan-400'   },
                    { label: 'Streaming',      value: 'Server-Sent Events',     color: 'text-teal-400'   },
                    { label: 'Provenance',     value: 'Full audit trail',       color: 'text-emerald-400'},
                    { label: 'Observability',  value: 'Langfuse tracing',       color: 'text-amber-400'  },
                    { label: 'Security',       value: 'Rate limit · CSP · HSTS',color: 'text-rose-400'   },
                  ].map(item => (
                    <div key={item.label} className="bg-[#0a0a1a] rounded-lg p-3 border border-[#2a2a4a]">
                      <div className="text-slate-600 mb-1">{item.label}</div>
                      <div className={`font-semibold ${item.color}`}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </main>

      {/* Share modal — portal-like, rendered outside the grid */}
      {showShare && sessionId && (
        <ShareModal
          sessionId={sessionId}
          sessionName={sessionName || sessionId}
          onClose={() => setShowShare(false)}
        />
      )}
    </div>
  );
}
