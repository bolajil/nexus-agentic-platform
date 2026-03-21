'use client';
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') ?? 'http://localhost:8003';

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('nexus_access_token') : null;
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

type ReviewAction = 'approve' | 'request_changes' | 'reject';

interface Review {
  id: string;
  session_id: string;
  reviewer_id: string;
  reviewer_name: string;
  action: ReviewAction;
  comment: string;
  created_at: string;
}

interface ReviewStatus {
  session_id: string;
  total: number;
  counts: Record<ReviewAction, number>;
  decision: 'pending' | 'approved' | 'changes_requested' | 'rejected';
  reviews: Review[];
}

const ACTION_META: Record<ReviewAction, { label: string; emoji: string; color: string; ring: string }> = {
  approve:         { label: 'Approve',          emoji: '✅', color: 'text-emerald-400', ring: 'border-emerald-500/50 bg-emerald-900/20' },
  request_changes: { label: 'Request Changes',  emoji: '🔄', color: 'text-amber-400',   ring: 'border-amber-500/50 bg-amber-900/20'   },
  reject:          { label: 'Reject',           emoji: '❌', color: 'text-red-400',     ring: 'border-red-500/50 bg-red-900/20'       },
};

const DECISION_META = {
  pending:          { label: 'Awaiting Review',    color: 'text-slate-400',   border: 'border-slate-500/30', bg: 'bg-slate-900/30'   },
  approved:         { label: 'Approved ✅',        color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-950/30' },
  changes_requested:{ label: 'Changes Requested 🔄',color:'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-950/30'   },
  rejected:         { label: 'Rejected ❌',        color: 'text-red-400',     border: 'border-red-500/30', bg: 'bg-red-950/30'     },
};

function timeAgo(iso: string): string {
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60)   return 'just now';
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400)return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

function Initials({ name }: { name: string }) {
  return (
    <>{name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()}</>
  );
}

interface ReviewPanelProps {
  sessionId: string;
}

export default function ReviewPanel({ sessionId }: ReviewPanelProps) {
  const [status, setStatus]       = useState<ReviewStatus | null>(null);
  const [myAction, setMyAction]   = useState<ReviewAction | null>(null);
  const [comment, setComment]     = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]         = useState('');
  const [myUserId, setMyUserId]   = useState('');

  useEffect(() => {
    try {
      const stored = localStorage.getItem('nexus_user');
      if (stored) {
        const u = JSON.parse(stored);
        setMyUserId(u.id ?? '');
      }
    } catch {}
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/reviews/${sessionId}/status`, {
        headers: authHeaders(),
      });
      if (res.ok) setStatus(await res.json());
    } catch {}
  }, [sessionId]);

  useEffect(() => {
    fetchStatus();
    // Pre-fill my existing review if any
  }, [fetchStatus]);

  // Pre-fill form with my existing review
  useEffect(() => {
    if (!status || !myUserId) return;
    const mine = status.reviews.find(r => r.reviewer_id === myUserId);
    if (mine) {
      setMyAction(mine.action);
      setComment(mine.comment);
    }
  }, [status, myUserId]);

  const submit = async () => {
    if (!myAction) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/v1/reviews/${sessionId}`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ action: myAction, comment }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Submit failed');
      await fetchStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const decision = status?.decision ?? 'pending';
  const dm = DECISION_META[decision];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#0d0d1f]/80 backdrop-blur-xl border border-[#2a2a4a] rounded-2xl p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <span className="w-5 h-5 rounded bg-indigo-600/30 flex items-center justify-center text-indigo-400 text-xs">◈</span>
          Team Review
        </h2>
        <button
          onClick={fetchStatus}
          className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Decision badge */}
      <div className={`mb-5 px-4 py-3 rounded-xl border ${dm.border} ${dm.bg} flex items-center justify-between`}>
        <span className={`font-semibold text-sm ${dm.color}`}>{dm.label}</span>
        {status && (
          <span className="text-[11px] text-slate-500">{status.total} vote{status.total !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Vote counts */}
      {status && status.total > 0 && (
        <div className="flex gap-3 mb-5">
          {(Object.entries(ACTION_META) as [ReviewAction, typeof ACTION_META[ReviewAction]][]).map(([action, meta]) => (
            <div key={action} className={`flex-1 text-center py-2 rounded-lg border ${
              status.counts[action] > 0 ? meta.ring : 'border-[#1e1e38] bg-[#0a0a1a]'
            }`}>
              <div className="text-base">{meta.emoji}</div>
              <div className={`text-lg font-bold ${status.counts[action] > 0 ? meta.color : 'text-slate-700'}`}>
                {status.counts[action]}
              </div>
              <div className="text-[9px] text-slate-600 uppercase tracking-wider">{action === 'request_changes' ? 'Changes' : meta.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* My vote */}
      <div className="mb-5">
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Your vote</div>
        <div className="flex gap-2 mb-3">
          {(Object.entries(ACTION_META) as [ReviewAction, typeof ACTION_META[ReviewAction]][]).map(([action, meta]) => (
            <button
              key={action}
              onClick={() => setMyAction(action)}
              className={`flex-1 py-2.5 rounded-xl border text-xs font-semibold transition-all ${
                myAction === action
                  ? meta.ring + ' ' + meta.color
                  : 'border-[#2a2a4a] text-slate-600 hover:text-slate-400 hover:border-slate-600'
              }`}
            >
              <span className="block text-base mb-0.5">{meta.emoji}</span>
              {action === 'request_changes' ? 'Changes' : meta.label}
            </button>
          ))}
        </div>

        <textarea
          rows={2}
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Add a comment (optional) — explain your decision or list what needs to change…"
          className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 resize-none"
        />

        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

        <button
          onClick={submit}
          disabled={!myAction || submitting}
          className="mt-3 w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Submitting…
            </span>
          ) : myAction && status?.reviews.some(r => r.reviewer_id === myUserId)
            ? 'Update Vote'
            : 'Submit Vote'
          }
        </button>
      </div>

      {/* Review list */}
      <AnimatePresence>
        {status && status.reviews.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">All Reviews</div>
            <div className="space-y-2">
              {status.reviews.map(review => {
                const meta = ACTION_META[review.action];
                return (
                  <motion.div
                    key={review.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex gap-3 p-3 rounded-xl bg-[#0a0a1a] border border-[#1e1e38]"
                  >
                    {/* Avatar */}
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-bold shrink-0 mt-0.5">
                      <Initials name={review.reviewer_name} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-semibold text-slate-300">{review.reviewer_name}</span>
                        <span className={`text-[10px] font-semibold ${meta.color}`}>
                          {meta.emoji} {meta.label}
                        </span>
                        <span className="text-[10px] text-slate-600 ml-auto">{timeAgo(review.created_at)}</span>
                      </div>
                      {review.comment && (
                        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{review.comment}</p>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {status && status.total === 0 && (
        <div className="text-center py-6 text-slate-700 text-xs">
          No reviews yet. Share this design with your team to start the review process.
        </div>
      )}
    </motion.div>
  );
}
