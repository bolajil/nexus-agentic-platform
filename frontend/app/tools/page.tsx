'use client';
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';

// ── Tool definitions ──────────────────────────────────────────────────────────

interface ConfigField { key: string; label: string; placeholder: string; type?: string }

interface ToolDef {
  id: string;
  name: string;
  category: string;
  icon: string;
  description: string;
  protocol: string;
  color: string;
  agents: string[];
  autoConnect: boolean;         // no config needed
  configFields?: ConfigField[];
  installHint?: string;
}

const TOOLS: ToolDef[] = [
  // ── Always-available (auto connect) ──────────────────────────────────────
  {
    id: 'openai', name: 'OpenAI (GPT-4o)', category: 'Core LLM', icon: '⬡',
    description: 'Primary LLM powering all 6 agents. Tool calling, JSON mode, embeddings.',
    protocol: 'OpenAI REST API', color: 'indigo', agents: ['All agents'],
    autoConnect: true,
  },
  {
    id: 'scipy', name: 'SciPy Optimizer', category: 'Math / Simulation', icon: '◉',
    description: 'Numerical optimization, ODE solving, curve fitting. Runs in-process.',
    protocol: 'Python importlib', color: 'cyan', agents: ['Simulation', 'Optimization'],
    autoConnect: true,
  },
  {
    id: 'numpy', name: 'NumPy Linear Algebra', category: 'Math / Simulation', icon: '◎',
    description: 'Matrix ops, FFT, eigenvalue decomposition, polynomial fitting.',
    protocol: 'Python importlib', color: 'cyan', agents: ['Simulation'],
    autoConnect: true,
  },
  {
    id: 'sympy', name: 'SymPy Symbolic Math', category: 'Math / Simulation', icon: '◈',
    description: 'Symbolic integration, Laplace transforms, differential equations.',
    protocol: 'Python importlib', color: 'cyan', agents: ['Research', 'Simulation'],
    autoConnect: true,
  },
  {
    id: 'nist', name: 'NIST WebBook', category: 'Materials DB', icon: '◇',
    description: 'Thermophysical fluid properties — saturation, transport, ideal gas data.',
    protocol: 'HTTPS REST', color: 'emerald', agents: ['Research'],
    autoConnect: true,
  },
  // ── Needs local install ───────────────────────────────────────────────────
  {
    id: 'freecad', name: 'FreeCAD', category: 'CAD / Geometry', icon: '◫',
    description: 'Open-source parametric CAD. Part design, FEM prep, STEP/STL export.',
    protocol: 'subprocess CLI', color: 'purple', agents: ['Design'],
    autoConnect: false,
    installHint: 'Download free at freecad.org',
    configFields: [
      { key: 'path', label: 'Executable path (optional)', placeholder: 'C:\\Program Files\\FreeCAD 1.0\\bin\\FreeCADCmd.exe' },
    ],
  },
  {
    id: 'openfoam', name: 'OpenFOAM', category: 'CFD / Thermal', icon: '◑',
    description: 'Open-source CFD. Mesh generation, turbulent flow, post-processing.',
    protocol: 'subprocess CLI', color: 'blue', agents: ['Simulation'],
    autoConnect: false,
    installHint: 'Install from openfoam.org + source the environment',
    configFields: [
      { key: 'path', label: 'OpenFOAM bin path (optional)', placeholder: '/opt/openfoam11/bin' },
    ],
  },
  // ── Commercial / hosted (configurable) ───────────────────────────────────
  {
    id: 'ansys', name: 'ANSYS Mechanical', category: 'FEA / Structural', icon: '◈',
    description: 'Structural, thermal, fatigue FEA. Topology optimisation. gRPC interface.',
    protocol: 'PyANSYS gRPC', color: 'purple', agents: ['Simulation', 'Optimization'],
    autoConnect: false,
    configFields: [
      { key: 'host', label: 'Host', placeholder: 'localhost' },
      { key: 'port', label: 'Port', placeholder: '50055', type: 'number' },
      { key: 'api_key', label: 'License server key', placeholder: 'your-license-key', type: 'password' },
    ],
  },
  {
    id: 'matlab', name: 'MATLAB Engine', category: 'Math / Simulation', icon: '◉',
    description: 'MATLAB Engine API — run .m scripts, Simulink models, control toolbox.',
    protocol: 'MATLAB Engine HTTP', color: 'amber', agents: ['Simulation', 'Optimization'],
    autoConnect: false,
    configFields: [
      { key: 'host', label: 'MATLAB Engine host', placeholder: 'localhost' },
      { key: 'port', label: 'Port', placeholder: '9910', type: 'number' },
    ],
  },
  {
    id: 'solidworks', name: 'SolidWorks REST Bridge', category: 'CAD / Geometry', icon: '◫',
    description: '3D parametric CAD — parts, assemblies, drawings, STEP export via REST bridge.',
    protocol: 'REST (COM API bridge)', color: 'indigo', agents: ['Design'],
    autoConnect: false,
    configFields: [
      { key: 'host', label: 'Bridge host', placeholder: 'localhost' },
      { key: 'port', label: 'Port', placeholder: '8085', type: 'number' },
      { key: 'api_key', label: 'API key', placeholder: 'your-api-key', type: 'password' },
    ],
  },
  {
    id: 'granta', name: 'Granta MI', category: 'Materials DB', icon: '⬡',
    description: 'Aerospace MMPDS, composites, RoHS data. CES EduPack integration.',
    protocol: 'Granta MI REST API', color: 'emerald', agents: ['Research'],
    autoConnect: false,
    configFields: [
      { key: 'host', label: 'Granta MI server', placeholder: 'granta.internal' },
      { key: 'port', label: 'Port', placeholder: '9000', type: 'number' },
      { key: 'api_key', label: 'API key', placeholder: 'your-mi-api-key', type: 'password' },
    ],
  },
  {
    id: 'teamcenter', name: 'Siemens Teamcenter', category: 'PLM / PDM', icon: '◑',
    description: 'BOM management, part numbering, ECO workflows, document control.',
    protocol: 'Teamcenter REST', color: 'rose', agents: ['Report'],
    autoConnect: false,
    configFields: [
      { key: 'host', label: 'Teamcenter host', placeholder: 'tc.internal' },
      { key: 'port', label: 'Port', placeholder: '4000', type: 'number' },
      { key: 'api_key', label: 'Service account token', placeholder: 'Bearer ...', type: 'password' },
    ],
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

const COLOR: Record<string, { border: string; text: string; bg: string }> = {
  indigo:  { border: 'border-indigo-500/30',  text: 'text-indigo-400',  bg: 'bg-indigo-900/20' },
  purple:  { border: 'border-purple-500/30',  text: 'text-purple-400',  bg: 'bg-purple-900/20' },
  blue:    { border: 'border-blue-500/30',    text: 'text-blue-400',    bg: 'bg-blue-900/20'   },
  cyan:    { border: 'border-cyan-500/30',    text: 'text-cyan-400',    bg: 'bg-cyan-900/20'   },
  emerald: { border: 'border-emerald-500/30', text: 'text-emerald-400', bg: 'bg-emerald-900/20'},
  amber:   { border: 'border-amber-500/30',   text: 'text-amber-400',   bg: 'bg-amber-900/20'  },
  rose:    { border: 'border-rose-500/30',    text: 'text-rose-400',    bg: 'bg-rose-900/20'   },
};

const AGENT_COLOR: Record<string, string> = {
  'All agents': 'bg-indigo-900/40 text-indigo-300',
  Research:     'bg-purple-900/30 text-purple-400',
  Design:       'bg-blue-900/30 text-blue-400',
  Simulation:   'bg-cyan-900/30 text-cyan-400',
  Optimization: 'bg-emerald-900/30 text-emerald-400',
  Report:       'bg-amber-900/30 text-amber-400',
};

// ── Configure Modal ───────────────────────────────────────────────────────────

function ConfigModal({
  tool, onClose, onConnect,
}: {
  tool: ToolDef;
  onClose: () => void;
  onConnect: (config: Record<string, string>) => void;
}) {
  const [form, setForm] = useState<Record<string, string>>({});

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="glass-card w-full max-w-md p-6 m-4"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-white">{tool.name}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{tool.protocol}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-lg">✕</button>
        </div>

        {tool.installHint && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-amber-900/20 border border-amber-500/20 text-xs text-amber-400">
            ⚠ {tool.installHint}
          </div>
        )}

        <div className="space-y-3 mb-5">
          {(tool.configFields || []).map(f => (
            <div key={f.key}>
              <label className="block text-xs text-slate-400 mb-1">{f.label}</label>
              <input
                type={f.type || 'text'}
                placeholder={f.placeholder}
                value={form[f.key] || ''}
                onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 font-mono"
              />
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg text-sm text-slate-400 border border-[#2a2a4a] hover:border-slate-500 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => { onConnect(form); onClose(); }}
            className="flex-1 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 transition-all"
          >
            Connect
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ── Add Custom Tool Modal ─────────────────────────────────────────────────────

const CONNECT_TYPES = [
  { value: 'http',      label: 'HTTP/REST',         hint: 'Ping host:port/path and check HTTP status' },
  { value: 'python',    label: 'Python module',      hint: 'import the module and call a test function' },
  { value: 'subprocess',label: 'Subprocess / CLI',   hint: 'Run a shell command and capture output' },
];

function AddToolModal({ onClose, onAdd }: {
  onClose: () => void;
  onAdd: (tool: ToolDef) => void;
}) {
  const [form, setForm] = useState({
    name: '', category: 'Custom', icon: '⚙', description: '',
    protocol: '', connectType: 'http',
    host: 'localhost', port: '8080', path: '/health',
    command: '', module: '',
    agents: 'Simulation',
  });

  const set = (k: string, v: string) => setForm(prev => ({ ...prev, [k]: v }));

  const handleAdd = () => {
    if (!form.name.trim()) return;
    const id = form.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const configFields: ConfigField[] = form.connectType === 'http'
      ? [
          { key: 'host', label: 'Host', placeholder: form.host },
          { key: 'port', label: 'Port', placeholder: form.port, type: 'number' },
          { key: 'path', label: 'Health path', placeholder: form.path },
          { key: 'api_key', label: 'API key (optional)', placeholder: 'Bearer ...', type: 'password' },
        ]
      : form.connectType === 'subprocess'
      ? [{ key: 'path', label: 'Executable path', placeholder: form.command || '/usr/bin/tool' }]
      : [{ key: 'path', label: 'Python module path', placeholder: form.module || 'mypackage.tool' }];

    onAdd({
      id,
      name: form.name,
      category: form.category || 'Custom',
      icon: form.icon || '⚙',
      description: form.description,
      protocol: form.protocol || form.connectType,
      color: 'amber',
      agents: form.agents.split(',').map(s => s.trim()).filter(Boolean),
      autoConnect: false,
      configFields,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="glass-card w-full max-w-lg p-6 m-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-bold text-white">Add Custom Tool</h3>
            <p className="text-xs text-slate-500 mt-0.5">Register any MCP-compatible engineering tool</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-lg">✕</button>
        </div>

        <div className="space-y-4">
          {/* Basic info */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-slate-400 mb-1">Tool name *</label>
              <input value={form.name} onChange={e => set('name', e.target.value)}
                placeholder="e.g. ANSYS Fluent, OpenFOAM, Abaqus"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Icon</label>
              <input value={form.icon} onChange={e => set('icon', e.target.value)}
                placeholder="⚙"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm text-center focus:outline-none focus:border-indigo-500/60" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Category</label>
              <input value={form.category} onChange={e => set('category', e.target.value)}
                placeholder="CFD / Thermal, FEA, Materials DB…"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Protocol label</label>
              <input value={form.protocol} onChange={e => set('protocol', e.target.value)}
                placeholder="REST API, gRPC, Python API…"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Description</label>
            <textarea value={form.description} onChange={e => set('description', e.target.value)}
              rows={2} placeholder="What this tool does and which agents will use it…"
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 resize-none" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Agents (comma-separated)</label>
            <input value={form.agents} onChange={e => set('agents', e.target.value)}
              placeholder="Research, Simulation, Optimization"
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
          </div>

          {/* Connection type */}
          <div>
            <label className="block text-xs text-slate-400 mb-2">Connection type</label>
            <div className="grid grid-cols-3 gap-2">
              {CONNECT_TYPES.map(ct => (
                <button
                  key={ct.value}
                  onClick={() => set('connectType', ct.value)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all text-left ${
                    form.connectType === ct.value
                      ? 'bg-indigo-900/30 text-indigo-300 border-indigo-500/40'
                      : 'text-slate-400 border-[#2a2a4a] hover:border-indigo-500/30'
                  }`}
                >
                  <div className="font-semibold">{ct.label}</div>
                  <div className="text-[10px] text-slate-600 mt-0.5 leading-tight">{ct.hint}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Connection-specific config */}
          {form.connectType === 'http' && (
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-1">
                <label className="block text-xs text-slate-400 mb-1">Host</label>
                <input value={form.host} onChange={e => set('host', e.target.value)}
                  placeholder="localhost"
                  className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Port</label>
                <input value={form.port} onChange={e => set('port', e.target.value)}
                  placeholder="8080" type="number"
                  className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Health path</label>
                <input value={form.path} onChange={e => set('path', e.target.value)}
                  placeholder="/health"
                  className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
              </div>
            </div>
          )}
          {form.connectType === 'subprocess' && (
            <div>
              <label className="block text-xs text-slate-400 mb-1">Command / executable path</label>
              <input value={form.command} onChange={e => set('command', e.target.value)}
                placeholder="/usr/bin/my-tool --version"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
            </div>
          )}
          {form.connectType === 'python' && (
            <div>
              <label className="block text-xs text-slate-400 mb-1">Python module name</label>
              <input value={form.module} onChange={e => set('module', e.target.value)}
                placeholder="mypackage.engineering_tool"
                className="w-full px-3 py-2 rounded-lg bg-[#0a0a1a] border border-[#2a2a4a] text-slate-300 text-sm font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500/60" />
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose}
            className="flex-1 py-2 rounded-lg text-sm text-slate-400 border border-[#2a2a4a] hover:border-slate-500 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleAdd}
            disabled={!form.name.trim()}
            className="flex-1 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:from-amber-500 hover:to-orange-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            + Add Tool
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ── Tool Card ─────────────────────────────────────────────────────────────────

function ToolCard({ tool, serverState, onAction }: {
  tool: ToolDef;
  serverState: Record<string, unknown> | null;
  onAction: (action: 'connect' | 'disconnect' | 'test' | 'configure') => void;
}) {
  const col = COLOR[tool.color];
  const status = serverState?.status as string | undefined;
  const isConnected = status === 'connected';
  const isLoading = status === 'loading';
  const isError = status === 'error';
  const testResult = serverState?.test_result as string | undefined;
  const version = serverState?.version as string | undefined;
  const capabilities = serverState?.capabilities as string[] | undefined;
  const errorMsg = serverState?.error as string | undefined;

  return (
    <motion.div
      layout
      className={`glass-card border ${col.border} overflow-hidden`}
    >
      {/* Header */}
      <div className={`px-5 py-4 ${col.bg} flex items-start gap-3`}>
        <span className={`text-xl ${col.text} flex-shrink-0 mt-0.5`}>{tool.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm text-white">{tool.name}</span>
            {/* Status badge */}
            {isLoading && (
              <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-600/30">
                <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="inline-block">↻</motion.span>
                Connecting…
              </span>
            )}
            {isConnected && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-900/40 text-emerald-400 border border-emerald-500/30">
                ● Connected
              </span>
            )}
            {isError && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-900/30 text-red-400 border border-red-500/30">
                ✕ Error
              </span>
            )}
            {status === 'unavailable' && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-500 border border-slate-600/30">
                Not installed
              </span>
            )}
            {status === 'disconnected' && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-500 border border-slate-600/30">
                Disconnected
              </span>
            )}
            {!status && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-600 border border-[#2a2a4a]">
                Not connected
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">{tool.description}</p>
          <div className="text-[10px] text-slate-600 font-mono mt-1">{tool.protocol}</div>
        </div>
      </div>

      {/* Agent tags */}
      <div className="px-5 py-2 flex flex-wrap gap-1.5 border-b border-[#1a1a2e]">
        {tool.agents.map(a => (
          <span key={a} className={`text-[9px] px-2 py-0.5 rounded-full ${AGENT_COLOR[a] || 'bg-slate-800 text-slate-400'}`}>
            {a}
          </span>
        ))}
        {version && (
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-slate-800/50 text-slate-500 font-mono ml-auto">
            v{version.replace(/^v/, '').slice(0, 20)}
          </span>
        )}
      </div>

      {/* Result / error output */}
      <AnimatePresence>
        {(testResult || errorMsg) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-5 py-3 border-b border-[#1a1a2e]"
          >
            <div className={`text-[11px] font-mono rounded-lg px-3 py-2.5 leading-relaxed ${
              isError || status === 'unavailable'
                ? 'bg-red-950/30 text-red-400 border border-red-900/30'
                : 'bg-black/30 text-emerald-400 border border-emerald-900/20'
            }`}>
              {errorMsg || testResult}
            </div>
            {capabilities && capabilities.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {capabilities.map(c => (
                  <span key={c} className={`text-[9px] px-1.5 py-0.5 rounded border ${col.border} ${col.text} font-mono`}>
                    {c}
                  </span>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Action buttons */}
      <div className="px-5 py-3 flex gap-2 flex-wrap">
        {!isConnected && !isLoading && (
          <button
            onClick={() => onAction(tool.autoConnect ? 'connect' : 'configure')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              tool.autoConnect
                ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
                : 'bg-[#1e1e38] hover:bg-indigo-900/30 text-indigo-400 border border-indigo-500/30 hover:border-indigo-500/60'
            }`}
          >
            {tool.autoConnect ? '⚡ Connect' : '⚙ Configure & Connect'}
          </button>
        )}

        {isLoading && (
          <button disabled className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-500 cursor-not-allowed">
            Connecting…
          </button>
        )}

        {isConnected && (
          <>
            <button
              onClick={() => onAction('test')}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-400 border border-emerald-500/30 transition-all"
            >
              ▶ Run Test
            </button>
            <button
              onClick={() => onAction('disconnect')}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-500 border border-[#2a2a4a] hover:border-red-500/30 hover:text-red-400 transition-all"
            >
              Disconnect
            </button>
          </>
        )}

        {(isError || status === 'unavailable' || status === 'disconnected') && (
          <button
            onClick={() => onAction(tool.autoConnect ? 'connect' : 'configure')}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-400 border border-[#2a2a4a] hover:border-indigo-500/30 hover:text-indigo-400 transition-all"
          >
            ↺ Retry
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ToolConnectionsPage() {
  // Map of toolId → server state
  const [states, setStates] = useState<Record<string, Record<string, unknown>>>({});
  const [configuring, setConfiguring] = useState<ToolDef | null>(null);
  const [addingTool, setAddingTool] = useState(false);
  const [customTools, setCustomTools] = useState<ToolDef[]>([]);
  const [filter, setFilter] = useState<string>('all');

  // Load existing connections from backend on mount
  useEffect(() => {
    fetch('/api/tools')
      .then(r => r.json())
      .then((list: Array<{ id: string } & Record<string, unknown>>) => {
        const map: Record<string, Record<string, unknown>> = {};
        list.forEach(item => { map[item.id] = item; });
        setStates(map);
      })
      .catch(() => {});
  }, []);

  const setToolState = (id: string, state: Record<string, unknown>) => {
    setStates(prev => ({ ...prev, [id]: state }));
  };

  const connect = useCallback(async (tool: ToolDef, config: Record<string, string> = {}) => {
    setToolState(tool.id, { status: 'loading' });
    try {
      const body = Object.keys(config).length > 0 ? config : {};
      const r = await fetch(`/api/tools/${tool.id}?action=connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      setToolState(tool.id, data);
    } catch (e) {
      setToolState(tool.id, { status: 'error', error: String(e) });
    }
  }, []);

  const disconnect = useCallback(async (toolId: string) => {
    const r = await fetch(`/api/tools/${toolId}`, { method: 'DELETE' });
    const data = await r.json();
    setToolState(toolId, data);
  }, []);

  const test = useCallback(async (tool: ToolDef) => {
    setToolState(tool.id, { ...states[tool.id], status: 'loading' });
    try {
      const r = await fetch(`/api/tools/${tool.id}?action=test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await r.json();
      setToolState(tool.id, data);
    } catch (e) {
      setToolState(tool.id, { status: 'error', error: String(e) });
    }
  }, [states]);

  const handleAction = (tool: ToolDef, action: 'connect' | 'disconnect' | 'test' | 'configure') => {
    if (action === 'connect')     connect(tool);
    else if (action === 'disconnect') disconnect(tool.id);
    else if (action === 'test')   test(tool);
    else if (action === 'configure') setConfiguring(tool);
  };

  // Stats
  const allTools = [...TOOLS, ...customTools];
  const connected = Object.values(states).filter(s => s.status === 'connected').length;
  const categories = [...new Set(allTools.map(t => t.category))];
  const filtered = filter === 'all' ? allTools : allTools.filter(t => t.category === filter);

  const connectAll = async () => {
    const autoTools = TOOLS.filter(t => t.autoConnect);
    for (const tool of autoTools) await connect(tool);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Tool Connections</h1>
            <p className="text-slate-400 mt-1 text-sm">
              Live MCP tool registry — click Connect to establish a real connection
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setAddingTool(true)}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-amber-600 hover:bg-amber-500 text-white transition-all"
            >
              + Add Tool
            </button>
            <button
              onClick={connectAll}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 transition-all nexus-glow"
            >
              ⚡ Connect All Auto
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Connected',  value: connected,       color: 'text-emerald-400' },
            { label: 'Available',  value: allTools.length,    color: 'text-indigo-400' },
            { label: 'Auto-connect', value: allTools.filter(t => t.autoConnect).length, color: 'text-cyan-400' },
            { label: 'Custom',       value: customTools.length, color: 'text-amber-400' },
          ].map(s => (
            <div key={s.label} className="glass-card p-4 text-center">
              <div className={`text-2xl font-bold ${s.color} mb-1`}>{s.value}</div>
              <div className="text-xs text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* MCP info strip */}
        <div className="glass-card p-4 mb-6 border border-indigo-500/20 bg-indigo-950/10 flex items-center gap-4">
          <span className="text-2xl">⬡</span>
          <div className="flex-1">
            <span className="text-sm font-semibold text-indigo-300">Model Context Protocol (MCP)</span>
            <span className="text-xs text-slate-500 ml-2">— Anthropic open standard</span>
            <p className="text-xs text-slate-500 mt-0.5">
              Each connected tool becomes a callable MCP server. NEXUS agents invoke them as structured tool calls — the same way they call OpenAI functions, but backed by real CAD/FEA/lab software.
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0 text-[10px] font-mono">
            {['active', 'connected'].includes(states['openai']?.status as string) ? (
              <span className="px-2 py-1 rounded-full bg-emerald-900/30 text-emerald-400 border border-emerald-500/20">Core active</span>
            ) : (
              <span className="px-2 py-1 rounded-full bg-slate-800 text-slate-500 border border-[#2a2a4a]">OpenAI not verified</span>
            )}
          </div>
        </div>

        {/* Category filter */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              filter === 'all'
                ? 'bg-indigo-600 text-white border-indigo-500'
                : 'text-slate-400 border-[#2a2a4a] hover:text-slate-200'
            }`}
          >
            All ({allTools.length})
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(filter === cat ? 'all' : cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                filter === cat
                  ? 'bg-[#1e1e38] text-indigo-300 border-indigo-500/40'
                  : 'text-slate-400 border-[#2a2a4a] hover:text-slate-200'
              }`}
            >
              {cat} ({allTools.filter(t => t.category === cat).length})
            </button>
          ))}
        </div>

        {/* Tool grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {filtered.map((tool, i) => (
            <motion.div
              key={tool.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <ToolCard
                tool={tool}
                serverState={states[tool.id] || null}
                onAction={action => handleAction(tool, action)}
              />
            </motion.div>
          ))}
        </div>

        {/* Modals */}
        <AnimatePresence>
          {configuring && (
            <ConfigModal
              tool={configuring}
              onClose={() => setConfiguring(null)}
              onConnect={config => connect(configuring, config)}
            />
          )}
          {addingTool && (
            <AddToolModal
              onClose={() => setAddingTool(false)}
              onAdd={tool => {
                setCustomTools(prev => [...prev, tool]);
                setConfiguring(tool);
              }}
            />
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
