'use client';
import { useState, FormEvent } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';
import AnoAI from '@/components/ui/animated-shader-background';

export default function ChangePasswordPage() {
  const { user, changePassword, logout } = useAuth();
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd,     setNewPwd]     = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [error,      setError]      = useState('');
  const [loading,    setLoading]    = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (newPwd !== confirmPwd) { setError('New passwords do not match.'); return; }
    if (newPwd.length < 8)     { setError('New password must be at least 8 characters.'); return; }
    if (newPwd === currentPwd) { setError('New password must be different from the current password.'); return; }
    setLoading(true);
    try {
      await changePassword(currentPwd, newPwd);
    } catch (err: any) {
      setError(err.message ?? 'Password change failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">

      {/* Aurora background */}
      <div className="fixed inset-0 z-0">
        <AnoAI />
      </div>
      <div className="fixed inset-0 z-0 bg-black/55" />

      <div className="relative z-10 min-h-screen flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <div className="bg-[#0d0d1f]/80 backdrop-blur-xl border border-amber-500/30 rounded-2xl shadow-2xl shadow-amber-500/10 p-8">

            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white shadow-lg shadow-amber-500/40 animate-float">
                🔑
              </div>
              <div>
                <div className="font-bold text-white text-lg tracking-wide">Change Password</div>
                <div className="text-[10px] text-slate-400 uppercase tracking-widest">Required before continuing</div>
              </div>
            </div>

            {/* Notice banner */}
            <div className="mb-6 px-4 py-3 rounded-lg bg-amber-950/40 border border-amber-500/30">
              <p className="text-amber-300 text-sm font-medium">Security requirement</p>
              <p className="text-amber-400/70 text-xs mt-0.5">
                {user?.role === 'admin'
                  ? 'The default admin password must be changed before accessing the platform.'
                  : 'You are required to set a new password before continuing.'}
              </p>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mb-5 px-4 py-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-400 text-sm"
              >
                {error}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">
                  Current Password
                </label>
                <input
                  type="password"
                  value={currentPwd}
                  onChange={e => setCurrentPwd(e.target.value)}
                  placeholder="Your current password"
                  required
                  className="w-full bg-[#0a0a1a]/80 border border-[#2a2a4a] rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/40 transition-colors backdrop-blur-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">
                  New Password
                </label>
                <input
                  type="password"
                  value={newPwd}
                  onChange={e => setNewPwd(e.target.value)}
                  placeholder="Min. 8 characters"
                  required
                  className="w-full bg-[#0a0a1a]/80 border border-[#2a2a4a] rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/40 transition-colors backdrop-blur-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wider">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmPwd}
                  onChange={e => setConfirmPwd(e.target.value)}
                  placeholder="••••••••"
                  required
                  className={`w-full bg-[#0a0a1a]/80 border rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 transition-colors backdrop-blur-sm ${
                    confirmPwd && newPwd !== confirmPwd
                      ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/30'
                      : 'border-[#2a2a4a] focus:border-amber-500 focus:ring-amber-500/40'
                  }`}
                />
                {confirmPwd && newPwd !== confirmPwd && (
                  <p className="mt-1 text-xs text-red-400">Passwords do not match</p>
                )}
              </div>

              {/* Password strength hints */}
              {newPwd && (
                <ul className="text-[11px] space-y-1 px-1">
                  {[
                    { ok: newPwd.length >= 8,                     label: 'At least 8 characters' },
                    { ok: /[A-Z]/.test(newPwd),                   label: 'Uppercase letter' },
                    { ok: /[0-9]/.test(newPwd),                   label: 'Number' },
                    { ok: /[^A-Za-z0-9]/.test(newPwd),            label: 'Special character' },
                  ].map(({ ok, label }) => (
                    <li key={label} className={`flex items-center gap-1.5 ${ok ? 'text-emerald-400' : 'text-slate-600'}`}>
                      <span>{ok ? '✓' : '○'}</span> {label}
                    </li>
                  ))}
                </ul>
              )}

              <button
                type="submit"
                disabled={loading || (!!confirmPwd && newPwd !== confirmPwd)}
                className="w-full py-3 mt-2 rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-semibold text-sm transition-all shadow-lg shadow-amber-500/20 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Updating password…
                  </span>
                ) : 'Set New Password'}
              </button>
            </form>

            <button
              onClick={logout}
              className="mt-4 w-full text-center text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
              Sign out instead
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
