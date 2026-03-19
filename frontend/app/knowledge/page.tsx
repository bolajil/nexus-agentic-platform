'use client';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';

interface KnowledgeStats {
  total_documents: number;
  domains?: string[];
}

interface SearchResult {
  title?: string;
  content?: string;
  domain?: string;
  score?: number;
}

const DOMAINS = ['heat_transfer', 'propulsion', 'structural', 'electronics_cooling'];

export default function KnowledgePage() {
  const [stats, setStats]         = useState<KnowledgeStats | null>(null);
  const [query, setQuery]         = useState('');
  const [domain, setDomain]       = useState('');
  const [results, setResults]     = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [seeding, setSeeding]     = useState(false);
  const [seedMsg, setSeedMsg]     = useState('');

  useEffect(() => {
    fetch('/api/knowledge').then(r => r.json()).then(setStats).catch(() => null);
  }, []);

  const search = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setResults([]);
    try {
      const params = new URLSearchParams({ q: query });
      if (domain) params.set('domain', domain);
      const res = await fetch(`/api/knowledge?${params}`);
      setResults(await res.json());
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const seedKB = async () => {
    setSeeding(true);
    setSeedMsg('');
    try {
      const res = await fetch('/api/knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ _seed: true }),
      });
      const data = await res.json();
      setSeedMsg(`Seeded ${data.ingested ?? '?'} documents`);
      const s = await fetch('/api/knowledge').then(r => r.json());
      setStats(s);
    } catch {
      setSeedMsg('Seed failed');
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Knowledge Base</h1>
          <p className="text-slate-400 mt-1 text-sm">Engineering reference documents powering the Research Agent's semantic search</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Stats */}
          <div className="xl:col-span-1 space-y-4">
            <div className="glass-card p-5">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Stats</div>
              <div className="text-4xl font-bold text-white mb-1">
                {stats?.total_documents ?? '—'}
              </div>
              <div className="text-slate-400 text-sm">Documents indexed</div>

              {stats?.domains && (
                <div className="mt-4 space-y-1.5">
                  {stats.domains.map(d => (
                    <div key={d} className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-indigo-500" />
                      <span className="text-xs text-slate-400">{d.replace('_', ' ')}</span>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={seedKB}
                disabled={seeding}
                className="mt-4 w-full py-2.5 rounded-lg text-sm font-medium bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-colors disabled:opacity-50"
              >
                {seeding ? 'Seeding…' : '↑ Seed Knowledge Base'}
              </button>
              {seedMsg && <div className="text-xs text-emerald-400 mt-2 text-center">{seedMsg}</div>}
            </div>

            <div className="glass-card p-5">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">How it Works</div>
              <div className="text-xs text-slate-400 space-y-2 leading-relaxed">
                <p>Documents are embedded using <span className="text-indigo-300">text-embedding-3-small</span> and stored in ChromaDB.</p>
                <p>The Research Agent queries this store using <span className="text-indigo-300">cosine similarity</span> to retrieve the most relevant engineering reference material.</p>
                <p>Retrieved chunks are injected into the LLM context as grounding for design calculations.</p>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="xl:col-span-2 space-y-4">
            <div className="glass-card p-5">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Semantic Search</div>
              <div className="flex gap-3 mb-3">
                <input
                  type="text"
                  placeholder="e.g. 'heat sink convection coefficient' or 'rocket specific impulse'"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && search()}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 placeholder-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition-colors"
                />
                <select
                  value={domain}
                  onChange={e => setDomain(e.target.value)}
                  className="px-3 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm focus:outline-none focus:border-indigo-500/60"
                >
                  <option value="">All domains</option>
                  {DOMAINS.map(d => (
                    <option key={d} value={d}>{d.replace('_', ' ')}</option>
                  ))}
                </select>
                <button
                  onClick={search}
                  disabled={!query.trim() || searching}
                  className="px-5 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-40 transition-colors"
                >
                  {searching ? '…' : 'Search'}
                </button>
              </div>
            </div>

            {results.length > 0 && (
              <div className="space-y-3">
                {results.map((r, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="glass-card p-4"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="font-semibold text-sm text-white">{r.title || 'Untitled'}</div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {r.domain && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-900/30 text-purple-400 border border-purple-500/20 uppercase">
                            {r.domain.replace('_', ' ')}
                          </span>
                        )}
                        {r.score !== undefined && (
                          <span className="text-[10px] text-slate-500 font-mono">
                            {(r.score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed line-clamp-4 font-mono">
                      {r.content}
                    </p>
                  </motion.div>
                ))}
              </div>
            )}

            {!searching && results.length === 0 && query && (
              <div className="text-center text-slate-600 py-8 text-sm">No results found</div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
