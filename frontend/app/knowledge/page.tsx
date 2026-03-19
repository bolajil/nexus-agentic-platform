'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';

// ── Types ─────────────────────────────────────────────────────────────────────

interface KnowledgeStats {
  total_documents: number;
  domains?: string[];
  collection_name?: string;
  embedding_model?: string;
}

interface SearchResult {
  title?: string;
  content?: string;
  domain?: string;
  score?: number;
  source?: string;
  project_id?: string;
}

interface IngestedDoc {
  doc_id: string;
  title: string;
  filename: string;
  domain: string;
  project_id: string;
  total_chunks: number;
  ingested_at: string;
  size_bytes: number;
}

interface UploadResult {
  doc_id: string;
  title: string;
  chunks_created: number;
  chunks_ingested: number;
  size_mb: number;
  technical_terms_found: string[];
  status: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const DOMAINS = [
  { value: 'heat_transfer',       label: 'Heat Transfer' },
  { value: 'propulsion',          label: 'Propulsion' },
  { value: 'structural',          label: 'Structural' },
  { value: 'electronics_cooling', label: 'Electronics Cooling' },
  { value: 'general',             label: 'General Engineering' },
];

const ACCEPTED_TYPES = '.pdf,.docx,.txt,.md';

// ── Upload Zone Component ─────────────────────────────────────────────────────

function UploadZone({
  onFiles,
  disabled,
}: {
  onFiles: (files: FileList) => void;
  disabled: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
  }, [onFiles]);

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
        dragging
          ? 'border-indigo-500 bg-indigo-950/30'
          : disabled
          ? 'border-[#2a2a4a] opacity-50 cursor-not-allowed'
          : 'border-[#2a2a4a] hover:border-indigo-500/60 hover:bg-indigo-950/10'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        multiple
        className="hidden"
        onChange={e => e.target.files && onFiles(e.target.files)}
        disabled={disabled}
      />
      <div className="text-3xl mb-3">📁</div>
      <div className="text-sm font-medium text-slate-300 mb-1">
        {dragging ? 'Drop files here' : 'Drag & drop files or click to browse'}
      </div>
      <div className="text-xs text-slate-500">
        Supported: <span className="text-slate-400">PDF · DOCX · TXT · MD</span>
        &nbsp;· Max 50MB per file
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function KnowledgePage() {
  // Stats & search
  const [stats, setStats]             = useState<KnowledgeStats | null>(null);
  const [query, setQuery]             = useState('');
  const [filterDomain, setFilterDomain] = useState('');
  const [results, setResults]         = useState<SearchResult[]>([]);
  const [searching, setSearching]     = useState(false);

  // Documents list
  const [docs, setDocs]               = useState<IngestedDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);

  // Upload form
  const [tab, setTab]                 = useState<'search' | 'upload' | 'library'>('search');
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadDomain, setUploadDomain] = useState('general');
  const [uploadProject, setUploadProject] = useState('default');
  const [uploadGlossary, setUploadGlossary] = useState('');
  const [uploading, setUploading]     = useState(false);
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [uploadError, setUploadError] = useState('');

  // Seed
  const [seeding, setSeeding]         = useState(false);
  const [seedMsg, setSeedMsg]         = useState('');

  // ── Load stats on mount ─────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/knowledge')
      .then(r => r.json())
      .then(setStats)
      .catch(() => null);
  }, []);

  // ── Load document library ───────────────────────────────────────────
  const loadDocs = useCallback(() => {
    setDocsLoading(true);
    fetch('/api/documents')
      .then(r => r.json())
      .then(data => setDocs(Array.isArray(data) ? data : []))
      .catch(() => setDocs([]))
      .finally(() => setDocsLoading(false));
  }, []);

  useEffect(() => {
    if (tab === 'library') loadDocs();
  }, [tab, loadDocs]);

  // ── Search ──────────────────────────────────────────────────────────
  const search = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setResults([]);
    try {
      const params = new URLSearchParams({ q: query });
      if (filterDomain) params.set('domain', filterDomain);
      const res = await fetch(`/api/knowledge?${params}`);
      const data = await res.json();
      setResults(Array.isArray(data) ? data : []);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  // ── Upload ──────────────────────────────────────────────────────────
  const handleFileDrop = (files: FileList) => {
    setUploadFiles(prev => [
      ...prev,
      ...Array.from(files).filter(f => !prev.find(p => p.name === f.name)),
    ]);
  };

  const removeFile = (name: string) => {
    setUploadFiles(prev => prev.filter(f => f.name !== name));
  };

  const submitUpload = async () => {
    if (!uploadFiles.length || uploading) return;
    setUploading(true);
    setUploadResults([]);
    setUploadError('');

    const results: UploadResult[] = [];

    for (const file of uploadFiles) {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('domain', uploadDomain);
      fd.append('project_id', uploadProject);
      if (uploadGlossary.trim()) {
        fd.append('project_glossary', uploadGlossary.trim());
      }

      try {
        const res = await fetch('/api/documents', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) {
          setUploadError(`${file.name}: ${data.detail || 'Upload failed'}`);
        } else {
          results.push(data);
        }
      } catch (err) {
        setUploadError(`${file.name}: Network error`);
      }
    }

    setUploadResults(results);
    setUploading(false);
    if (results.length) {
      setUploadFiles([]);
      // Refresh stats
      fetch('/api/knowledge').then(r => r.json()).then(setStats).catch(() => null);
    }
  };

  // ── Delete document ─────────────────────────────────────────────────
  const deleteDoc = async (docId: string) => {
    await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    setDocs(prev => prev.filter(d => d.doc_id !== docId));
  };

  // ── Seed ────────────────────────────────────────────────────────────
  const seedKB = async () => {
    setSeeding(true);
    setSeedMsg('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/v1/knowledge/seed`, {
        method: 'POST',
      });
      const data = await res.json();
      setSeedMsg(`Seeded ${data.ingested ?? '?'} documents`);
      fetch('/api/knowledge').then(r => r.json()).then(setStats).catch(() => null);
    } catch {
      setSeedMsg('Seed failed — is backend running?');
    } finally {
      setSeeding(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="ml-60 flex-1 p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Knowledge Base</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Upload internal documents · Semantic search with terminology normalization · Project-scoped retrieval
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          {/* ── Left sidebar: stats ─────────────────────────────── */}
          <div className="xl:col-span-1 space-y-4">
            <div className="glass-card p-5">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Collection</div>
              <div className="text-4xl font-bold text-white mb-1">
                {stats?.total_documents ?? '—'}
              </div>
              <div className="text-slate-400 text-sm mb-3">Documents indexed</div>

              {stats?.domains && stats.domains.length > 0 && (
                <div className="space-y-1.5 mb-4">
                  {stats.domains.map(d => (
                    <div key={d} className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                      <span className="text-xs text-slate-400">{d.replace('_', ' ')}</span>
                    </div>
                  ))}
                </div>
              )}

              {stats?.embedding_model && (
                <div className="text-[10px] font-mono text-slate-600 mb-3">
                  {stats.embedding_model}
                </div>
              )}

              <button
                onClick={seedKB}
                disabled={seeding}
                className="w-full py-2 rounded-lg text-xs font-medium bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-colors disabled:opacity-50"
              >
                {seeding ? 'Seeding…' : '↑ Seed Built-in Docs'}
              </button>
              {seedMsg && (
                <div className={`text-xs mt-2 text-center ${seedMsg.includes('fail') ? 'text-red-400' : 'text-emerald-400'}`}>
                  {seedMsg}
                </div>
              )}
            </div>

            {/* Terminology info */}
            <div className="glass-card p-5">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">
                Terminology Handling
              </div>
              <div className="space-y-2 text-xs text-slate-400 leading-relaxed">
                <p>
                  Queries and documents are <span className="text-indigo-300">normalized</span> before embedding —
                  Greek letters and abbreviations are expanded to canonical English:
                </p>
                <div className="font-mono bg-black/30 rounded p-2 space-y-1 text-[10px] border border-white/5">
                  <div><span className="text-purple-400">θ_ja</span> → junction-to-ambient thermal resistance</div>
                  <div><span className="text-purple-400">η_f</span> → fin efficiency</div>
                  <div><span className="text-purple-400">Δv</span> → delta-v velocity change</div>
                  <div><span className="text-purple-400">Isp</span> → specific impulse</div>
                  <div><span className="text-purple-400">TIM</span> → thermal interface material</div>
                  <div><span className="text-purple-400">TWR</span> → thrust-to-weight ratio</div>
                </div>
                <p className="text-slate-500">
                  Add project-specific terms via the Upload tab → Project Glossary field.
                </p>
              </div>
            </div>
          </div>

          {/* ── Right: tabs ─────────────────────────────────────── */}
          <div className="xl:col-span-3 space-y-4">
            {/* Tab bar */}
            <div className="flex gap-1 bg-[#0a0a1a] p-1 rounded-xl w-fit border border-[#2a2a4a]">
              {(['search', 'upload', 'library'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-5 py-2 rounded-lg text-sm font-medium capitalize transition-all ${
                    tab === t ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {t === 'search' ? '🔍 Search' : t === 'upload' ? '↑ Upload' : '📚 Library'}
                </button>
              ))}
            </div>

            {/* ── SEARCH TAB ─────────────────────────────────────── */}
            {tab === 'search' && (
              <div className="space-y-4">
                <div className="glass-card p-5">
                  <div className="flex gap-3 mb-3">
                    <input
                      type="text"
                      placeholder="e.g. 'junction-to-ambient resistance' or 'θ_ja' or 'Isp 220s'"
                      value={query}
                      onChange={e => setQuery(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && search()}
                      className="flex-1 px-4 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 placeholder-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition-colors font-mono"
                    />
                    <select
                      value={filterDomain}
                      onChange={e => setFilterDomain(e.target.value)}
                      className="px-3 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm focus:outline-none focus:border-indigo-500/60"
                    >
                      <option value="">All domains</option>
                      {DOMAINS.map(d => (
                        <option key={d.value} value={d.value}>{d.label}</option>
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
                  <div className="text-[10px] text-slate-600">
                    Greek letters (θ, η, Δ, σ) and abbreviations (Isp, TIM, TWR) are automatically expanded before search
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
                            {r.project_id && r.project_id !== 'default' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-900/30 text-blue-400 border border-blue-500/20">
                                {r.project_id}
                              </span>
                            )}
                            {r.score !== undefined && (
                              <span className="text-[10px] font-mono text-slate-500">
                                {(r.score * 100).toFixed(0)}% match
                              </span>
                            )}
                          </div>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed line-clamp-5 font-mono">
                          {r.content}
                        </p>
                        {r.source && (
                          <div className="text-[10px] text-slate-600 mt-2">Source: {r.source}</div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                )}

                {!searching && results.length === 0 && query && (
                  <div className="text-center text-slate-600 py-8 text-sm">
                    No results. Try a different query or seed the knowledge base.
                  </div>
                )}
              </div>
            )}

            {/* ── UPLOAD TAB ─────────────────────────────────────── */}
            {tab === 'upload' && (
              <div className="space-y-4">
                <div className="glass-card p-6">
                  <h3 className="text-sm font-semibold text-slate-300 mb-4">
                    Upload Internal Documents
                  </h3>

                  <UploadZone onFiles={handleFileDrop} disabled={uploading} />

                  {/* Queued files */}
                  {uploadFiles.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {uploadFiles.map(f => (
                        <div key={f.name} className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a]">
                          <div>
                            <div className="text-xs text-slate-300 font-mono">{f.name}</div>
                            <div className="text-[10px] text-slate-600">
                              {(f.size / 1024).toFixed(0)} KB · {f.type || 'unknown type'}
                            </div>
                          </div>
                          <button
                            onClick={() => removeFile(f.name)}
                            className="text-slate-600 hover:text-red-400 text-xs transition-colors"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Upload options */}
                  <div className="mt-5 grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-500 mb-1.5 block">Domain</label>
                      <select
                        value={uploadDomain}
                        onChange={e => setUploadDomain(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm focus:outline-none focus:border-indigo-500/60"
                      >
                        {DOMAINS.map(d => (
                          <option key={d.value} value={d.value}>{d.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 mb-1.5 block">Project ID</label>
                      <input
                        type="text"
                        placeholder="default"
                        value={uploadProject}
                        onChange={e => setUploadProject(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm focus:outline-none focus:border-indigo-500/60 font-mono"
                      />
                    </div>
                  </div>

                  {/* Project glossary */}
                  <div className="mt-4">
                    <label className="text-xs text-slate-500 mb-1.5 block">
                      Project Glossary <span className="text-slate-700">(optional JSON — custom terminology for this project)</span>
                    </label>
                    <textarea
                      rows={3}
                      placeholder={'{"NEXUS-TPS": "NEXUS thermal protection system", "η_prop": "propulsive efficiency", "MY-ABBR": "expanded meaning"}'}
                      value={uploadGlossary}
                      onChange={e => setUploadGlossary(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 placeholder-slate-700 text-xs font-mono focus:outline-none focus:border-indigo-500/60 resize-none"
                    />
                    <div className="text-[10px] text-slate-600 mt-1">
                      Terms are expanded in both the document chunks AND search queries for this project, ensuring notation mismatches don't break retrieval.
                    </div>
                  </div>

                  {uploadError && (
                    <div className="mt-3 px-3 py-2 rounded-lg bg-red-900/20 border border-red-500/30 text-xs text-red-400">
                      {uploadError}
                    </div>
                  )}

                  <button
                    onClick={submitUpload}
                    disabled={!uploadFiles.length || uploading}
                    className="mt-5 w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-indigo-600 to-purple-600 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:from-indigo-500 hover:to-purple-500 transition-all"
                  >
                    {uploading ? (
                      <span className="flex items-center justify-center gap-2">
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                        />
                        Uploading & Indexing…
                      </span>
                    ) : `↑ Upload ${uploadFiles.length || ''} File${uploadFiles.length !== 1 ? 's' : ''}`}
                  </button>
                </div>

                {/* Upload results */}
                <AnimatePresence>
                  {uploadResults.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-3"
                    >
                      {uploadResults.map((r, i) => (
                        <div key={i} className="glass-card p-4 border-emerald-500/20">
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-emerald-400">✓</span>
                            <span className="font-semibold text-sm text-white">{r.title}</span>
                          </div>
                          <div className="grid grid-cols-3 gap-3 text-xs mb-3">
                            <div className="bg-black/20 p-2 rounded border border-white/5 text-center">
                              <div className="text-2xl font-bold text-indigo-400">{r.chunks_ingested}</div>
                              <div className="text-slate-500 mt-0.5">chunks indexed</div>
                            </div>
                            <div className="bg-black/20 p-2 rounded border border-white/5 text-center">
                              <div className="text-2xl font-bold text-purple-400">{r.size_mb}</div>
                              <div className="text-slate-500 mt-0.5">MB processed</div>
                            </div>
                            <div className="bg-black/20 p-2 rounded border border-white/5 text-center">
                              <div className="text-2xl font-bold text-teal-400">{r.technical_terms_found?.length ?? 0}</div>
                              <div className="text-slate-500 mt-0.5">terms extracted</div>
                            </div>
                          </div>
                          {r.technical_terms_found && r.technical_terms_found.length > 0 && (
                            <div>
                              <div className="text-[10px] text-slate-600 mb-1.5">Technical terms detected:</div>
                              <div className="flex flex-wrap gap-1">
                                {r.technical_terms_found.map(t => (
                                  <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-purple-900/20 text-purple-400 border border-purple-500/20 font-mono">
                                    {t}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* ── LIBRARY TAB ────────────────────────────────────── */}
            {tab === 'library' && (
              <div className="space-y-3">
                {docsLoading ? (
                  <div className="flex items-center gap-3 text-slate-500 py-8">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="w-4 h-4 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full"
                    />
                    Loading documents…
                  </div>
                ) : docs.length === 0 ? (
                  <div className="glass-card p-12 text-center">
                    <div className="text-4xl mb-3">📚</div>
                    <div className="text-slate-400 text-sm mb-3">No documents uploaded yet</div>
                    <button
                      onClick={() => setTab('upload')}
                      className="text-indigo-400 hover:text-indigo-300 text-sm transition-colors"
                    >
                      Upload your first document →
                    </button>
                  </div>
                ) : (
                  docs.map((doc, i) => (
                    <motion.div
                      key={doc.doc_id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04 }}
                      className="glass-card p-4"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-sm text-white truncate">{doc.title}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-900/30 text-purple-400 border border-purple-500/20 flex-shrink-0">
                              {doc.domain?.replace('_', ' ')}
                            </span>
                            {doc.project_id !== 'default' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-900/30 text-blue-400 border border-blue-500/20 flex-shrink-0">
                                {doc.project_id}
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 font-mono">{doc.filename}</div>
                          <div className="flex gap-4 mt-1 text-[10px] text-slate-600">
                            <span>{doc.total_chunks} chunks</span>
                            <span>{doc.size_bytes ? `${(doc.size_bytes / 1024).toFixed(0)} KB` : ''}</span>
                            <span>{doc.ingested_at ? new Date(doc.ingested_at).toLocaleDateString() : ''}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => deleteDoc(doc.doc_id)}
                          className="text-slate-600 hover:text-red-400 text-xs transition-colors flex-shrink-0 px-2 py-1 rounded hover:bg-red-900/20"
                          title="Delete document"
                        >
                          🗑
                        </button>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
