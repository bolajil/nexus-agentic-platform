'use client';
import { use, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import Sidebar from '../../components/Sidebar';
import ProvenanceChain from '../../components/ProvenanceChain';
import DesignDiagram from '../../components/DesignDiagram';

const StlViewer = dynamic(() => import('../../components/StlViewer'), { ssr: false });

interface Session {
  id: string;
  name: string;
  status: string;
  engineering_brief: string;
  requirements?: Record<string, unknown>;
  research_results?: Record<string, unknown>;
  design_params?: Record<string, unknown>;
  simulation_results?: Record<string, unknown>;
  optimized_params?: Record<string, unknown>;
  report?: Record<string, unknown>;
  provenance_chain?: unknown[];
  created_at: string;
}

function JsonSection({ title, data }: { title: string; data: unknown }) {
  const [open, setOpen] = useState(false);
  if (!data) return null;
  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#1e1e38] transition-colors"
      >
        <span className="font-semibold text-sm text-slate-300">{title}</span>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          className="text-slate-500 text-xs"
        >▾</motion.span>
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-[#2a2a4a]">
          <pre className="mt-3 text-[11px] text-slate-400 font-mono overflow-auto bg-black/30 p-4 rounded-lg leading-relaxed max-h-80">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function SessionDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'diagram' | 'cad' | 'provenance' | 'raw'>('overview');
  const [cadInfo, setCadInfo] = useState<{ available: boolean; has_stl?: boolean; has_step?: boolean } | null>(null);

  useEffect(() => {
    fetch(`/api/sessions/${id}`)
      .then(r => r.ok ? r.json() : null)
      .then(setSession)
      .finally(() => setLoading(false));
  }, [id]);

  // Poll for CAD file availability once session loads
  useEffect(() => {
    if (!session) return;
    fetch(`/api/cad/${id}?file=status`)
      .then(r => r.ok ? r.json() : { available: false })
      .then(setCadInfo)
      .catch(() => setCadInfo({ available: false }));
  }, [id, session]);

  if (loading) return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8 flex items-center text-slate-500 gap-3">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full"
        />
        Loading session…
      </main>
    </div>
  );

  if (!session) return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="text-slate-500">Session not found. <Link href="/sessions" className="text-indigo-400">← Back</Link></div>
      </main>
    </div>
  );

  const report = session.report as Record<string, unknown> | undefined;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/sessions" className="text-xs text-slate-500 hover:text-slate-300 mb-3 inline-block transition-colors">
            ← All Sessions
          </Link>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white">{session.name}</h1>
              <div className="text-xs text-slate-500 font-mono mt-1">{session.id}</div>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider border
              ${session.status === 'complete' ? 'bg-emerald-900/30 text-emerald-400 border-emerald-500/20' :
                session.status === 'running'  ? 'bg-indigo-900/30 text-indigo-400 border-indigo-500/20' :
                'bg-slate-800 text-slate-400 border-slate-600/20'}`}>
              {session.status}
            </span>
          </div>
        </div>

        {/* Brief */}
        <div className="glass-card p-5 mb-6">
          <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider font-medium">Engineering Brief</div>
          <p className="text-slate-300 text-sm leading-relaxed font-mono">{session.engineering_brief}</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-[#0a0a1a] p-1 rounded-xl w-fit border border-[#2a2a4a]">
          {(['overview', 'diagram', 'cad', 'provenance', 'raw'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize relative ${
                tab === t
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t}
              {t === 'cad' && cadInfo?.available && (
                <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500" />
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'overview' && (
          <div className="space-y-4">
            {report && (
              <div className="glass-card p-6">
                <h2 className="text-lg font-bold text-white mb-2">{report.title as string}</h2>
                <div className="space-y-4 text-sm">
                  {(['executive_summary', 'design_solution', 'simulation_results', 'optimization_results', 'conclusions'] as const).map(key => {
                    const val = report[key];
                    return val ? (
                      <div key={key}>
                        <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
                          {key.replace(/_/g, ' ')}
                        </div>
                        <div className="text-slate-400 text-xs leading-relaxed bg-black/20 p-3 rounded-lg border border-white/5">
                          {val as string}
                        </div>
                      </div>
                    ) : null;
                  })}
                  {Array.isArray(report.recommendations) && (
                    <div>
                      <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">Recommendations</div>
                      <ul className="space-y-1">
                        {(report.recommendations as string[]).map((r, i) => (
                          <li key={i} className="flex gap-2 text-xs text-slate-400">
                            <span className="text-indigo-500">→</span>{r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
            <JsonSection title="Requirements" data={session.requirements} />
            <JsonSection title="Research Results" data={session.research_results} />
            <JsonSection title="Design Parameters" data={session.design_params} />
            <JsonSection title="Simulation Results" data={session.simulation_results} />
            <JsonSection title="Optimized Parameters" data={session.optimized_params} />
          </div>
        )}

        {tab === 'diagram' && (
          <DesignDiagram
            domain={session.requirements ? (session.requirements as Record<string, unknown>).domain as string : undefined}
            designParams={session.design_params as Record<string, unknown>}
            simResults={session.simulation_results as Record<string, unknown>}
            optimizedParams={session.optimized_params as Record<string, unknown>}
          />
        )}

        {tab === 'cad' && (
          <div className="space-y-4">
            {cadInfo?.available ? (
              <>
                {/* Download buttons */}
                <div className="glass-card p-5 flex flex-wrap items-center gap-3">
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-white mb-1">CAD Geometry</div>
                    <div className="text-xs text-slate-500">Generated by FreeCAD · Download for CAD/FEM import</div>
                  </div>
                  {cadInfo.has_step && (
                    <a
                      href={`/api/cad/${id}?file=design.step`}
                      download="design.step"
                      className="px-5 py-2.5 rounded-xl text-sm font-semibold border border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/30 transition-all"
                    >
                      ⬇ STEP
                    </a>
                  )}
                  {cadInfo.has_stl && (
                    <a
                      href={`/api/cad/${id}?file=design.stl`}
                      download="design.stl"
                      className="px-5 py-2.5 rounded-xl text-sm font-semibold border border-purple-500/40 text-purple-300 hover:bg-purple-900/30 transition-all"
                    >
                      ⬇ STL
                    </a>
                  )}
                </div>

                {/* 3D viewer */}
                {cadInfo.has_stl && (
                  <div className="glass-card overflow-hidden">
                    <div className="px-5 py-3 border-b border-[#2a2a4a] flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">3D Preview</span>
                      <span className="text-[10px] text-slate-600">drag to rotate</span>
                    </div>
                    <StlViewer url={`/api/cad/${id}?file=design.stl`} />
                  </div>
                )}
              </>
            ) : (
              <div className="glass-card p-12 text-center">
                <div className="text-4xl mb-4 text-slate-600">◫</div>
                <div className="text-slate-400 text-sm mb-2">No CAD files for this session</div>
                <div className="text-slate-600 text-xs max-w-sm mx-auto">
                  FreeCAD must be installed and connected in the Tools page.
                  Run a new pipeline after connecting FreeCAD to generate STEP + STL geometry.
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'provenance' && (
          <ProvenanceChain entries={(session.provenance_chain || []) as Parameters<typeof ProvenanceChain>[0]['entries']} />
        )}

        {tab === 'raw' && (
          <div className="glass-card p-5">
            <pre className="text-[11px] text-slate-400 font-mono overflow-auto max-h-[70vh] leading-relaxed">
              {JSON.stringify(session, null, 2)}
            </pre>
          </div>
        )}
      </main>
    </div>
  );
}
