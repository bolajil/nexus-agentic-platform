'use client';

/**
 * DesignDiagram — Domain-aware SVG schematic generator with pan/zoom
 * Renders a zoomable technical diagram from agent design_params output.
 */

import { useRef, useState, useCallback } from 'react';

interface DiagramProps {
  domain?: string;
  designParams?: Record<string, unknown>;
  simResults?: Record<string, unknown>;
  optimizedParams?: Record<string, unknown>;
}

// ── Zoom/Pan wrapper ───────────────────────────────────────────────────────────
function ZoomableWrapper({ children }: { children: React.ReactNode }) {
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(null);

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const factor = e.deltaY < 0 ? 1.12 : 0.9;
    setScale(s => Math.min(Math.max(s * factor, 0.25), 8));
  }, []);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = { startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y };
  }, [pan]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current) return;
    setPan({
      x: dragRef.current.panX + (e.clientX - dragRef.current.startX),
      y: dragRef.current.panY + (e.clientY - dragRef.current.startY),
    });
  }, []);

  const onPointerUp = useCallback(() => { dragRef.current = null; }, []);

  const reset = useCallback(() => { setScale(1); setPan({ x: 0, y: 0 }); }, []);
  const zoomIn = useCallback(() => setScale(s => Math.min(s * 1.25, 8)), []);
  const zoomOut = useCallback(() => setScale(s => Math.max(s / 1.25, 0.25)), []);

  return (
    <div className="relative rounded-xl overflow-hidden border border-[#2a2a4a] bg-[#0a0a1a]">
      {/* Pan/zoom surface */}
      <div
        className="w-full flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
        style={{ minHeight: '220px', touchAction: 'none' }}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`, transformOrigin: 'center' }}>
          {children}
        </div>
      </div>

      {/* Controls overlay */}
      <div className="absolute bottom-2 right-2 flex items-center gap-1 z-10">
        <button onClick={zoomIn}
          className="w-6 h-6 rounded bg-[#1a1a2e]/90 border border-[#3a3a5a] text-slate-300 text-xs hover:bg-[#2a2a4a] flex items-center justify-center font-bold">+</button>
        <button onClick={zoomOut}
          className="w-6 h-6 rounded bg-[#1a1a2e]/90 border border-[#3a3a5a] text-slate-300 text-xs hover:bg-[#2a2a4a] flex items-center justify-center font-bold">−</button>
        <button onClick={reset}
          className="px-1.5 h-6 rounded bg-[#1a1a2e]/90 border border-[#3a3a5a] text-slate-400 text-[9px] hover:bg-[#2a2a4a]">⊙ reset</button>
        <span className="px-1.5 h-6 flex items-center rounded bg-[#1a1a2e]/90 border border-[#3a3a5a] text-slate-500 text-[9px]">{Math.round(scale * 100)}%</span>
      </div>

      {/* Hint (fade after first interaction) */}
      <div className="absolute top-2 left-2 text-[9px] text-slate-600 pointer-events-none">
        Scroll to zoom · Drag to pan
      </div>
    </div>
  );
}

// ── Dimension line helper ──────────────────────────────────────────────────────
function HDim({ x1, x2, y, label, color = '#475569' }: { x1: number; x2: number; y: number; label: string; color?: string }) {
  const mx = (x1 + x2) / 2;
  return (
    <g>
      <line x1={x1} y1={y} x2={x2} y2={y} stroke={color} strokeWidth="0.7" />
      <polygon points={`${x1},${y} ${x1 + 4},${y - 2} ${x1 + 4},${y + 2}`} fill={color} />
      <polygon points={`${x2},${y} ${x2 - 4},${y - 2} ${x2 - 4},${y + 2}`} fill={color} />
      <line x1={x1} y1={y - 3} x2={x1} y2={y + 3} stroke={color} strokeWidth="0.7" />
      <line x1={x2} y1={y - 3} x2={x2} y2={y + 3} stroke={color} strokeWidth="0.7" />
      <text x={mx} y={y - 4} fontSize="6" fill={color} textAnchor="middle">{label}</text>
    </g>
  );
}

function VDim({ x, y1, y2, label, color = '#475569' }: { x: number; y1: number; y2: number; label: string; color?: string }) {
  const my = (y1 + y2) / 2;
  return (
    <g>
      <line x1={x} y1={y1} x2={x} y2={y2} stroke={color} strokeWidth="0.7" />
      <polygon points={`${x},${y1} ${x - 2},${y1 + 4} ${x + 2},${y1 + 4}`} fill={color} />
      <polygon points={`${x},${y2} ${x - 2},${y2 - 4} ${x + 2},${y2 - 4}`} fill={color} />
      <line x1={x - 3} y1={y1} x2={x + 3} y2={y1} stroke={color} strokeWidth="0.7" />
      <line x1={x - 3} y1={y2} x2={x + 3} y2={y2} stroke={color} strokeWidth="0.7" />
      <text x={x + 5} y={my} fontSize="6" fill={color} dominantBaseline="middle">{label}</text>
    </g>
  );
}

// ── Heat Sink / Electronics Cooling Diagram ───────────────────────────────────
function HeatSinkDiagram({ dp, sim, opt }: { dp: Record<string, unknown>; sim: Record<string, unknown>; opt: Record<string, unknown> }) {
  const fins = Number(opt.num_fins ?? dp.num_fins ?? 12);
  const finH = Number(opt.fin_height_mm ?? dp.fin_height_mm ?? 30);
  const baseH = 8;
  const totalH = Math.min(finH, 55);
  const width = 300;
  const baseY = 150;
  const finCount = Math.min(fins, 18);
  const finSpacing = (width - 20) / Math.max(finCount, 1);
  const thermalR = Number(sim.thermal_resistance_C_per_W ?? opt.thermal_resistance ?? 0).toFixed(3);
  const maxTemp = Number(sim.max_component_temp_C ?? sim.junction_temp_C ?? 0).toFixed(1);
  const baseMat = String(dp.material ?? opt.material ?? 'Al 6061');

  // Dimension values from params
  const pitchMm = Number(opt.fin_pitch_mm ?? dp.fin_pitch_mm ?? (finSpacing * 0.8).toFixed(1));
  const widthMm = Number(dp.base_width_mm ?? opt.base_width_mm ?? 120);

  return (
    <svg viewBox="0 0 370 250" className="w-full rounded-none bg-[#0a0a1a]">
      {/* Air flow arrows */}
      {[50, 100, 155, 210, 265, 310].map((x, i) => (
        <g key={i}>
          <line x1={x} y1={18} x2={x} y2={55} stroke="#3b82f6" strokeWidth="1" strokeDasharray="3,3" opacity="0.4" />
          <polygon points={`${x},57 ${x - 4},50 ${x + 4},50`} fill="#3b82f6" opacity="0.5" />
        </g>
      ))}
      <text x="10" y="14" fontSize="7.5" fill="#3b82f6" opacity="0.7">↓ Forced Convection (3 m/s) ↓</text>

      {/* Fins */}
      {Array.from({ length: finCount }).map((_, i) => {
        const x = 20 + i * ((width - 20) / finCount);
        const gid = `fg${i}`;
        return (
          <g key={i}>
            <defs>
              <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#93c5fd" stopOpacity="0.15" />
              </linearGradient>
            </defs>
            <rect x={x} y={baseY - totalH} width={Math.max(finSpacing * 0.55, 3)} height={totalH}
              fill={`url(#${gid})`} stroke="#60a5fa" strokeWidth="0.5" rx="1" />
          </g>
        );
      })}

      {/* Base plate */}
      <defs>
        <linearGradient id="bpGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#4338ca" stopOpacity="0.9" />
        </linearGradient>
      </defs>
      <rect x={10} y={baseY} width={width + 20} height={baseH} fill="url(#bpGrad)" stroke="#818cf8" strokeWidth="1" rx="2" />
      <text x="175" y={baseY + 5.5} fontSize="7" fill="white" textAnchor="middle" dominantBaseline="middle">{baseMat} Base Plate</text>

      {/* Heat source */}
      <rect x={120} y={baseY + baseH} width={100} height={14} fill="#dc2626" opacity="0.8" rx="2" stroke="#f87171" strokeWidth="1" />
      <text x="170" y={baseY + baseH + 7} fontSize="7" fill="white" textAnchor="middle" dominantBaseline="middle">100 W Power Module</text>

      {/* PCB */}
      <rect x={60} y={baseY + baseH + 14} width={220} height={8} fill="#166534" opacity="0.8" rx="1" stroke="#4ade80" strokeWidth="0.5" />
      <text x="170" y={baseY + baseH + 18.5} fontSize="7" fill="#86efac" textAnchor="middle" dominantBaseline="middle">FR4 PCB</text>

      {/* ── Dimension lines ── */}
      {/* Fin height */}
      <VDim x={335} y1={baseY - totalH} y2={baseY} label={`${Math.round(finH)} mm`} color="#60a5fa" />
      {/* Base plate height */}
      <VDim x={350} y1={baseY} y2={baseY + baseH} label={`${baseH} mm`} color="#818cf8" />
      {/* Overall base width */}
      <HDim x1={10} x2={width + 20} y={baseY - totalH - 12} label={`${widthMm} mm`} color="#475569" />
      {/* Fin pitch */}
      {finCount > 1 && (
        <HDim x1={20} x2={20 + (width - 20) / finCount} y={baseY - totalH + 10} label={`pitch ${Number(pitchMm).toFixed(1)} mm`} color="#38bdf8" />
      )}

      {/* Metrics bar */}
      <rect x={0} y={228} width={370} height={22} fill="#0d0d20" />
      <text x="10" y="243" fontSize="7.5" fill="#a78bfa">θ_sa = {thermalR} °C/W</text>
      {maxTemp !== '0.0' && <text x="130" y="243" fontSize="7.5" fill="#f87171">T_junction = {maxTemp} °C</text>}
      <text x="270" y="243" fontSize="7.5" fill="#60a5fa">Fins: {fins}</text>
    </svg>
  );
}

// ── De Laval Nozzle / Propulsion Diagram ─────────────────────────────────────
function NozzleDiagram({ dp, sim, opt }: { dp: Record<string, unknown>; sim: Record<string, unknown>; opt: Record<string, unknown> }) {
  const Isp = Number(opt.Isp_s ?? dp.Isp_s ?? sim.Isp_s ?? 65).toFixed(0);
  const thrust = Number(opt.thrust_mN ?? dp.thrust_mN ?? sim.thrust_mN ?? 50).toFixed(1);
  const expRatio = Number(opt.expansion_ratio ?? dp.expansion_ratio ?? 8).toFixed(1);
  const throatDia = Number(opt.throat_diameter_mm ?? dp.throat_diameter_mm ?? 2.4).toFixed(1);
  const exitDia = Number(opt.exit_diameter_mm ?? dp.exit_diameter_mm ?? 6.8).toFixed(1);
  const chamberL = Number(dp.chamber_length_mm ?? opt.chamber_length_mm ?? 40).toFixed(0);

  return (
    <svg viewBox="0 0 370 220" className="w-full rounded-none bg-[#0a0a1a]">
      {/* Chamber */}
      <rect x={10} y={60} width={80} height={60} fill="#1e1e38" stroke="#6366f1" strokeWidth="1.5" rx="3" />
      <text x="50" y="85" fontSize="7" fill="#a5b4fc" textAnchor="middle">Propellant</text>
      <text x="50" y="95" fontSize="7" fill="#a5b4fc" textAnchor="middle">Chamber</text>
      <text x="50" y="107" fontSize="6.5" fill="#6366f1" textAnchor="middle">N₂ Gas</text>

      {/* Converging section */}
      <path d="M 90 63 L 162 82 L 162 98 L 90 117 Z" fill="#2a2a4a" stroke="#818cf8" strokeWidth="1" />

      {/* Throat */}
      <rect x={157} y={82} width={10} height={16} fill="#4f46e5" opacity="0.9" rx="1" />
      <text x="162" y="76" fontSize="6.5" fill="#818cf8" textAnchor="middle">★ throat</text>

      {/* Diverging section */}
      <path d="M 167 82 L 285 48 L 285 132 L 167 98 Z" fill="#1a1a32" stroke="#818cf8" strokeWidth="1" />

      {/* Exhaust plume */}
      <path d="M 285 90 Q 322 74 352 64" stroke="#f97316" strokeWidth="2" fill="none" opacity="0.6" />
      <path d="M 285 90 Q 328 90 358 90" stroke="#fbbf24" strokeWidth="2.5" fill="none" opacity="0.75" />
      <path d="M 285 90 Q 322 106 352 116" stroke="#f97316" strokeWidth="2" fill="none" opacity="0.6" />
      <text x="325" y="86" fontSize="7" fill="#fbbf24">Exhaust</text>

      {/* ── Dimension lines ── */}
      {/* Chamber length */}
      <HDim x1={10} x2={90} y={135} label={`${chamberL} mm`} color="#6366f1" />
      {/* Throat diameter (vertical) */}
      <VDim x={172} y1={82} y2={98} label={`⌀ ${throatDia} mm`} color="#818cf8" />
      {/* Exit diameter (vertical) */}
      <VDim x={292} y1={48} y2={132} label={`⌀ ${exitDia} mm`} color="#60a5fa" />

      {/* Pressure label */}
      <text x="30" y="155" fontSize="7" fill="#6366f1">P_chamber</text>
      <line x1="50" y1="158" x2="85" y2="117" stroke="#6366f1" strokeWidth="0.8" markerEnd="url(#arr)" />

      {/* Metrics bar */}
      <rect x={0} y={196} width={370} height={24} fill="#0d0d20" />
      <text x="10" y="212" fontSize="7.5" fill="#a78bfa">Isp = {Isp} s</text>
      <text x="100" y="212" fontSize="7.5" fill="#60a5fa">Thrust = {thrust} mN</text>
      <text x="225" y="212" fontSize="7.5" fill="#34d399">ε = {expRatio}</text>
      <text x="280" y="212" fontSize="7.5" fill="#f59e0b">3U CubeSat</text>
    </svg>
  );
}

// ── Structural / Bracket Diagram ─────────────────────────────────────────────
function StructuralDiagram({ dp, sim, opt }: { dp: Record<string, unknown>; sim: Record<string, unknown>; opt: Record<string, unknown> }) {
  const fos = Number(opt.factor_of_safety ?? sim.factor_of_safety ?? dp.factor_of_safety ?? 2.1).toFixed(2);
  const maxStress = Number(sim.max_von_mises_MPa ?? sim.max_stress_MPa ?? 0).toFixed(0);
  const mass = Number(opt.mass_kg ?? dp.mass_kg ?? 0).toFixed(3);
  const yieldStr = Number(dp.yield_strength_MPa ?? opt.yield_strength_MPa ?? 276).toFixed(0);
  const bracketL = Number(dp.bracket_length_mm ?? opt.bracket_length_mm ?? 150).toFixed(0);
  const bracketH = Number(dp.bracket_height_mm ?? opt.bracket_height_mm ?? 40).toFixed(0);
  const thickness = Number(dp.thickness_mm ?? opt.thickness_mm ?? 6).toFixed(1);

  return (
    <svg viewBox="0 0 370 240" className="w-full rounded-none bg-[#0a0a1a]">
      {/* Wall mount */}
      <rect x={10} y={45} width={20} height={120} fill="#374151" stroke="#6b7280" strokeWidth="1" />
      {[55, 70, 85, 100, 115, 130, 145].map(y => (
        <line key={y} x1={10} y1={y} x2={2} y2={y + 8} stroke="#6b7280" strokeWidth="1.5" />
      ))}
      <text x="20" y="42" fontSize="6.5" fill="#6b7280" textAnchor="middle">Wall</text>

      {/* Bracket body — Von Mises stress coloring */}
      <defs>
        <linearGradient id="vmGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#dc2626" stopOpacity="0.85" />
          <stop offset="40%" stopColor="#f97316" stopOpacity="0.65" />
          <stop offset="100%" stopColor="#22c55e" stopOpacity="0.45" />
        </linearGradient>
      </defs>
      <rect x={30} y={80} width={190} height={50} fill="url(#vmGrad)" stroke="#9ca3af" strokeWidth="1" rx="2" />
      <text x="125" y="107" fontSize="8" fill="white" textAnchor="middle" dominantBaseline="middle">Al 6061-T6 Bracket</text>

      {/* Gusset */}
      <path d="M 30 130 L 85 130 L 30 175 Z" fill="#4b5563" stroke="#6b7280" strokeWidth="0.8" />
      <text x="45" y="158" fontSize="6" fill="#9ca3af" transform="rotate(-50,45,158)">Gusset</text>

      {/* Mounting plate (right end) */}
      <rect x={220} y={70} width={15} height={70} fill="#374151" stroke="#6b7280" strokeWidth="1" />

      {/* Axial load arrow */}
      <line x1={318} y1={105} x2={240} y2={105} stroke="#ef4444" strokeWidth="2.5" />
      <polygon points="238,105 247,100 247,110" fill="#ef4444" />
      <text x={325} y={102} fontSize="8" fill="#ef4444" fontWeight="bold">500 N</text>

      {/* Moment arrow (curved) */}
      <path d="M 248 80 Q 278 68 278 105 Q 278 135 248 128" stroke="#f97316" strokeWidth="1.5" fill="none" />
      <polygon points="248,126 254,134 258,125" fill="#f97316" />
      <text x={282} y={105} fontSize="7" fill="#f97316">50 N·m</text>

      {/* ── Dimension lines ── */}
      {/* Bracket length */}
      <HDim x1={30} x2={220} y={185} label={`${bracketL} mm`} color="#9ca3af" />
      {/* Bracket height */}
      <VDim x={338} y1={80} y2={130} label={`${bracketH} mm`} color="#9ca3af" />
      {/* Thickness annotation */}
      <text x={222} y={78} fontSize="6" fill="#64748b">t={thickness}mm</text>

      {/* Von Mises stress color scale */}
      <rect x={30} y={200} width={190} height={8} fill="url(#vmGrad)" rx="2" />
      <text x={30} y={220} fontSize="6.5" fill="#dc2626">σ_vm high</text>
      <text x={210} y={220} fontSize="6.5" fill="#22c55e" textAnchor="end">σ_vm low</text>

      {/* Metrics bar */}
      <rect x={0} y={224} width={370} height={16} fill="#0d0d20" />
      {maxStress !== '0' && <text x={10} y={235} fontSize="7.5" fill="#f97316">σ_max = {maxStress} MPa</text>}
      <text x={140} y={235} fontSize="7.5" fill="#34d399">FOS = {fos}</text>
      <text x={210} y={235} fontSize="7.5" fill="#60a5fa">f_y = {yieldStr} MPa</text>
      {mass !== '0.000' && <text x={295} y={235} fontSize="7.5" fill="#a78bfa">m = {mass} kg</text>}
    </svg>
  );
}

// ── Generic Pipeline Diagram ──────────────────────────────────────────────────
function PipelineDiagram() {
  const nodes = [
    { x: 20,  label: 'REQ', color: '#6366f1', sub: 'Requirements' },
    { x: 85,  label: 'RES', color: '#8b5cf6', sub: 'Research' },
    { x: 150, label: 'DES', color: '#a78bfa', sub: 'Design' },
    { x: 215, label: 'SIM', color: '#60a5fa', sub: 'Simulation' },
    { x: 280, label: 'OPT', color: '#34d399', sub: 'Optimization' },
  ];

  return (
    <svg viewBox="0 0 370 140" className="w-full rounded-none bg-[#0a0a1a]">
      {nodes.map((n, i) => (
        <g key={n.label}>
          {i < nodes.length - 1 && (
            <line x1={n.x + 25} y1={55} x2={nodes[i + 1].x} y2={55} stroke="#2a2a4a" strokeWidth="2" />
          )}
          <circle cx={n.x + 12} cy={55} r={13} fill={n.color} opacity="0.15" stroke={n.color} strokeWidth="1.5" />
          <text x={n.x + 12} y={55} fontSize="6.5" fill={n.color} textAnchor="middle" dominantBaseline="middle" fontWeight="bold">{n.label}</text>
          <text x={n.x + 12} y={75} fontSize="6" fill="#64748b" textAnchor="middle">{n.sub}</text>
        </g>
      ))}
      {/* Report node */}
      <g>
        <line x1={305} y1={55} x2={340} y2={55} stroke="#2a2a4a" strokeWidth="2" />
        <rect x={340} y={43} width={22} height={24} fill="#f59e0b" opacity="0.15" stroke="#f59e0b" strokeWidth="1.5" rx="3" />
        <text x={351} y={55} fontSize="6.5" fill="#f59e0b" textAnchor="middle" dominantBaseline="middle">RPT</text>
        <text x={351} y={75} fontSize="6" fill="#64748b" textAnchor="middle">Report</text>
      </g>
      <text x={185} y={110} fontSize="7.5" fill="#475569" textAnchor="middle">LangGraph StateGraph · 6-Agent Autonomous Pipeline</text>
    </svg>
  );
}

/** Recursively flatten nested objects so agents' nested structures are searchable at the top level. */
function flatten(obj: Record<string, unknown>, depth = 2): Record<string, unknown> {
  const out: Record<string, unknown> = { ...obj };
  if (depth <= 0) return out;
  for (const [, v] of Object.entries(obj)) {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      const nested = flatten(v as Record<string, unknown>, depth - 1);
      for (const [nk, nv] of Object.entries(nested)) {
        if (!(nk in out)) out[nk] = nv;
      }
    }
  }
  return out;
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function DesignDiagram({ domain, designParams = {}, simResults = {}, optimizedParams = {} }: DiagramProps) {
  const dp  = flatten(designParams  as Record<string, unknown>);
  const sim = flatten(simResults    as Record<string, unknown>);
  const opt = flatten(optimizedParams as Record<string, unknown>);

  const label: Record<string, string> = {
    electronics_cooling: 'Heat Sink Cross-Section — Electronics Cooling',
    heat_transfer:       'Thermal Assembly Schematic',
    propulsion:          'De Laval Nozzle — Cold Gas Thruster',
    structural:          'Bracket Load & Von Mises Stress Distribution',
    general:             'Agent Pipeline Architecture',
  };

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-300">Design Schematic</h3>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-900/30 text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
          {domain?.replace(/_/g, ' ') || 'general'}
        </span>
      </div>

      <ZoomableWrapper>
        {domain === 'electronics_cooling' || domain === 'heat_transfer'
          ? <HeatSinkDiagram dp={dp} sim={sim} opt={opt} />
          : domain === 'propulsion'
          ? <NozzleDiagram dp={dp} sim={sim} opt={opt} />
          : domain === 'structural'
          ? <StructuralDiagram dp={dp} sim={sim} opt={opt} />
          : <PipelineDiagram />}
      </ZoomableWrapper>

      <div className="mt-2 text-[10px] text-slate-600">
        {label[domain ?? ''] ?? label.general} · Generated from agent output
      </div>
    </div>
  );
}
