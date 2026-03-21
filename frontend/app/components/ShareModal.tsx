'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') ?? 'http://localhost:8003';

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('nexus_access_token') : null;
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

interface ShareModalProps {
  sessionId: string;
  sessionName?: string;
  onClose: () => void;
}

type Channel = 'slack' | 'teams' | 'email';

const CHANNELS: { id: Channel; label: string; icon: string; color: string }[] = [
  { id: 'slack',  label: 'Slack',  icon: '◈', color: 'border-[#E01E5A]/40 bg-[#4A154B]/20 text-[#E01E5A]' },
  { id: 'teams',  label: 'Teams',  icon: '◉', color: 'border-[#7B83EB]/40 bg-[#464EB8]/20 text-[#7B83EB]' },
  { id: 'email',  label: 'Email',  icon: '✉', color: 'border-indigo-500/40 bg-indigo-900/20 text-indigo-400' },
];

export default function ShareModal({ sessionId, sessionName, onClose }: ShareModalProps) {
  const [selected, setSelected] = useState<Set<Channel>>(new Set(['slack']));
  const [note, setNote]         = useState('');
  const [emailTo, setEmailTo]   = useState('');
  const [status, setStatus]     = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');
  const [message, setMessage]   = useState('');

  const toggle = (ch: Channel) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(ch) ? next.delete(ch) : next.add(ch);
      return next;
    });
  };

  const share = async () => {
    if (selected.size === 0) return;
    setStatus('loading');
    try {
      const res = await fetch(`${API}/api/v1/integrations/share`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          session_id: sessionId,
          note,
          channels: Array.from(selected),
          email_to: emailTo.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Share failed');
      setStatus('ok');
      setMessage('Shared successfully! Your team has been notified.');
    } catch (err: any) {
      setStatus('error');
      setMessage(err.message);
    }
  };

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          onClick={e => e.stopPropagation()}
          className="w-full max-w-md bg-[#0d0d1f] border border-indigo-500/20 rounded-2xl shadow-2xl shadow-indigo-500/10 p-6"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="font-bold text-white text-base">Share for Review</div>
              <div className="text-xs text-slate-500 mt-0.5 truncate max-w-[280px]">
                {sessionName || sessionId}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-slate-600 hover:text-slate-300 transition-colors text-lg leading-none"
            >
              ✕
            </button>
          </div>

          {status !== 'ok' ? (
            <>
              {/* Channel selector */}
              <div className="mb-4">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Send to</div>
                <div className="flex gap-2">
                  {CHANNELS.map(ch => (
                    <button
                      key={ch.id}
                      type="button"
                      onClick={() => toggle(ch.id)}
                      className={`flex-1 py-2.5 rounded-xl border text-xs font-semibold transition-all ${
                        selected.has(ch.id)
                          ? ch.color
                          : 'border-[#2a2a4a] text-slate-600 hover:text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <span className="block text-base mb-0.5">{ch.icon}</span>
                      {ch.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Note */}
              <div className="mb-4">
                <label className="block text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                  Add a note (optional)
                </label>
                <textarea
                  rows={2}
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder="e.g. Ready for thermal review — please check the heat flux assumptions."
                  className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 resize-none"
                />
              </div>

              {/* Email override */}
              {selected.has('email') && (
                <div className="mb-4">
                  <label className="block text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                    Email recipients override (optional)
                  </label>
                  <input
                    type="text"
                    value={emailTo}
                    onChange={e => setEmailTo(e.target.value)}
                    placeholder="Leave blank to use configured recipients"
                    className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60"
                  />
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 mt-2">
                <button
                  onClick={share}
                  disabled={selected.size === 0 || status === 'loading'}
                  className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  {status === 'loading' ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Sharing…
                    </span>
                  ) : '↗ Share'}
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl border border-[#2a2a4a] text-slate-400 hover:text-slate-200 text-sm transition-colors"
                >
                  Cancel
                </button>
              </div>

              {status === 'error' && (
                <p className="mt-3 text-xs text-red-400">{message}</p>
              )}
            </>
          ) : (
            /* Success state */
            <div className="text-center py-6">
              <div className="text-4xl mb-3">✓</div>
              <div className="text-emerald-400 font-semibold text-sm mb-1">Shared!</div>
              <div className="text-slate-500 text-xs">{message}</div>
              <button
                onClick={onClose}
                className="mt-5 px-5 py-2 rounded-xl border border-[#2a2a4a] text-slate-400 hover:text-slate-200 text-sm transition-colors"
              >
                Close
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
