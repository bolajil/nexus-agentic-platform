'use client';
import { useState, useEffect, FormEvent } from 'react';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import AnoAI from '@/components/ui/animated-shader-background';

const API = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') ?? 'http://localhost:8003';

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('nexus_access_token') : null;
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

interface SmtpConfig {
  host: string; port: number; user: string; password: string; from_addr: string; use_tls: boolean;
}
interface IntegrationsConfig {
  slack_webhook?: string;
  teams_webhook?: string;
  smtp?: SmtpConfig;
  email_recipients?: string[];
}

const DEFAULT_SMTP: SmtpConfig = { host: '', port: 465, user: '', password: '', from_addr: '', use_tls: true };

type Status = { type: 'idle' | 'loading' | 'ok' | 'error'; msg?: string };

function StatusBadge({ s }: { s: Status }) {
  if (s.type === 'idle') return null;
  if (s.type === 'loading') return (
    <span className="text-xs text-slate-400 flex items-center gap-1">
      <span className="w-3 h-3 border border-slate-400 border-t-transparent rounded-full animate-spin" /> Sending…
    </span>
  );
  if (s.type === 'ok') return <span className="text-xs text-emerald-400">✓ {s.msg}</span>;
  return <span className="text-xs text-red-400">✗ {s.msg}</span>;
}

export default function IntegrationsPage() {
  const [cfg, setCfg] = useState<IntegrationsConfig>({});
  const [smtp, setSmtp] = useState<SmtpConfig>(DEFAULT_SMTP);
  const [recipients, setRecipients] = useState('');
  const [saveStatus, setSaveStatus]   = useState<Status>({ type: 'idle' });
  const [slackStatus, setSlackStatus] = useState<Status>({ type: 'idle' });
  const [teamsStatus, setTeamsStatus] = useState<Status>({ type: 'idle' });
  const [emailStatus, setEmailStatus] = useState<Status>({ type: 'idle' });

  useEffect(() => {
    fetch(`${API}/api/v1/integrations`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : {})
      .then((data: IntegrationsConfig) => {
        setCfg(data);
        if (data.smtp) setSmtp(data.smtp);
        if (data.email_recipients) setRecipients(data.email_recipients.join(', '));
      })
      .catch(() => {});
  }, []);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setSaveStatus({ type: 'loading' });
    try {
      const body: IntegrationsConfig = {
        ...cfg,
        smtp: smtp.host ? smtp : undefined,
        email_recipients: recipients.split(',').map(s => s.trim()).filter(Boolean),
      };
      const res = await fetch(`${API}/api/v1/integrations`, {
        method: 'POST', headers: authHeaders(), body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Save failed');
      setSaveStatus({ type: 'ok', msg: 'Settings saved' });
    } catch (err: any) {
      setSaveStatus({ type: 'error', msg: err.message });
    }
  };

  const test = async (
    channel: 'slack' | 'teams' | 'email',
    setStatus: (s: Status) => void,
  ) => {
    setStatus({ type: 'loading' });
    try {
      const res = await fetch(`${API}/api/v1/integrations/test/${channel}`, {
        method: 'POST', headers: authHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Test failed');
      setStatus({ type: 'ok', msg: data.message });
    } catch (err: any) {
      setStatus({ type: 'error', msg: err.message });
    }
  };

  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    opts: { type?: string; placeholder?: string } = {}
  ) => (
    <div>
      <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">{label}</label>
      <input
        type={opts.type ?? 'text'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={opts.placeholder}
        className="w-full bg-[#0a0a1a] border border-[#2a2a4a] rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-colors"
      />
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <div className="fixed inset-0 z-0"><AnoAI /></div>
      <div className="fixed inset-0 z-0 bg-black/60" />
      <Sidebar />

      <main className="relative z-10 ml-60 flex-1 p-8 max-w-4xl">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-white mb-1">Integrations</h1>
          <p className="text-slate-400 text-sm mb-8">
            Connect Slack, Teams, and email so your team gets notified when a design is ready for review.
          </p>
        </motion.div>

        <form onSubmit={save} className="space-y-6">

          {/* ── Slack ─────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="bg-[#0d0d1f]/80 backdrop-blur-xl border border-[#2a2a4a] rounded-2xl p-6"
          >
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-[#4A154B] flex items-center justify-center text-lg">
                <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#E01E5A]">
                  <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
                </svg>
              </div>
              <div>
                <div className="font-semibold text-white text-sm">Slack</div>
                <div className="text-[11px] text-slate-500">Incoming webhook notifications</div>
              </div>
            </div>

            {field('Incoming Webhook URL', cfg.slack_webhook ?? '', v => setCfg(c => ({ ...c, slack_webhook: v })), {
              placeholder: 'https://hooks.slack.com/services/T.../B.../...',
            })}

            <div className="flex items-center gap-3 mt-3">
              <button
                type="button"
                onClick={() => test('slack', setSlackStatus)}
                disabled={!cfg.slack_webhook}
                className="text-xs px-3 py-1.5 rounded-lg border border-[#2a2a4a] text-slate-400 hover:text-slate-200 hover:border-indigo-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Send test
              </button>
              <StatusBadge s={slackStatus} />
            </div>
          </motion.div>

          {/* ── Teams ─────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-[#0d0d1f]/80 backdrop-blur-xl border border-[#2a2a4a] rounded-2xl p-6"
          >
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-[#464EB8]/20 flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#7B83EB]">
                  <path d="M20.625 4.5H14.25V3a.75.75 0 0 0-.75-.75H10.5a.75.75 0 0 0-.75.75v1.5H3.375A1.125 1.125 0 0 0 2.25 5.625v12.75A1.125 1.125 0 0 0 3.375 19.5h17.25a1.125 1.125 0 0 0 1.125-1.125V5.625A1.125 1.125 0 0 0 20.625 4.5zm-8.25 9.375H9.75V12h2.625v1.875zm0-3H9.75V9h2.625v1.875zm3.375 3h-2.625V12H15.75v1.875zm0-3h-2.625V9H15.75v1.875z"/>
                </svg>
              </div>
              <div>
                <div className="font-semibold text-white text-sm">Microsoft Teams</div>
                <div className="text-[11px] text-slate-500">Incoming webhook with Adaptive Cards</div>
              </div>
            </div>

            {field('Incoming Webhook URL', cfg.teams_webhook ?? '', v => setCfg(c => ({ ...c, teams_webhook: v })), {
              placeholder: 'https://outlook.office.com/webhook/...',
            })}

            <div className="flex items-center gap-3 mt-3">
              <button
                type="button"
                onClick={() => test('teams', setTeamsStatus)}
                disabled={!cfg.teams_webhook}
                className="text-xs px-3 py-1.5 rounded-lg border border-[#2a2a4a] text-slate-400 hover:text-slate-200 hover:border-indigo-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Send test
              </button>
              <StatusBadge s={teamsStatus} />
            </div>
          </motion.div>

          {/* ── Email (SMTP) ───────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-[#0d0d1f]/80 backdrop-blur-xl border border-[#2a2a4a] rounded-2xl p-6"
          >
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-indigo-600/20 flex items-center justify-center text-indigo-400 text-lg">✉</div>
              <div>
                <div className="font-semibold text-white text-sm">Email (SMTP)</div>
                <div className="text-[11px] text-slate-500">Gmail, Outlook, SendGrid, etc.</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {field('SMTP Host', smtp.host, v => setSmtp(s => ({ ...s, host: v })), { placeholder: 'smtp.gmail.com' })}
              {field('Port', String(smtp.port), v => setSmtp(s => ({ ...s, port: Number(v) || 465 })), { placeholder: '465' })}
              {field('Username', smtp.user, v => setSmtp(s => ({ ...s, user: v })), { placeholder: 'you@gmail.com' })}
              {field('Password / App Password', smtp.password, v => setSmtp(s => ({ ...s, password: v })), { type: 'password', placeholder: '••••••••' })}
            </div>
            <div className="mt-3">
              {field('From Address', smtp.from_addr, v => setSmtp(s => ({ ...s, from_addr: v })), { placeholder: 'NEXUS Platform <nexus@yourdomain.com>' })}
            </div>
            <div className="mt-3">
              {field('Recipients (comma-separated)', recipients, setRecipients, { placeholder: 'alice@acme.com, bob@acme.com' })}
            </div>
            <div className="flex items-center gap-2 mt-3">
              <input
                type="checkbox"
                id="use_tls"
                checked={smtp.use_tls}
                onChange={e => setSmtp(s => ({ ...s, use_tls: e.target.checked }))}
                className="w-4 h-4 rounded accent-indigo-500"
              />
              <label htmlFor="use_tls" className="text-xs text-slate-400">Use SSL/TLS (port 465)</label>
            </div>

            <div className="flex items-center gap-3 mt-4">
              <button
                type="button"
                onClick={() => test('email', setEmailStatus)}
                disabled={!smtp.host}
                className="text-xs px-3 py-1.5 rounded-lg border border-[#2a2a4a] text-slate-400 hover:text-slate-200 hover:border-indigo-500/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Send test email
              </button>
              <StatusBadge s={emailStatus} />
            </div>
          </motion.div>

          {/* ── Save ──────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-4"
          >
            <button
              type="submit"
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-500/20"
            >
              Save Settings
            </button>
            <StatusBadge s={saveStatus} />
          </motion.div>
        </form>

        {/* How-to hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-5"
        >
          <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-3">How it works</div>
          <ol className="space-y-2 text-xs text-slate-400 list-decimal list-inside">
            <li>Run a pipeline on Mission Control — it generates an engineering report.</li>
            <li>Click <strong className="text-slate-300">Share for Review</strong> on the completed report.</li>
            <li>Your team receives a Slack/Teams message or email with a link to the result.</li>
            <li>Each team member opens NEXUS and submits a vote: <strong className="text-emerald-400">Approve</strong>, <strong className="text-amber-400">Request Changes</strong>, or <strong className="text-red-400">Reject</strong>.</li>
            <li>A notification is sent back to the channel when the team reaches a decision.</li>
          </ol>
        </motion.div>
      </main>
    </div>
  );
}
