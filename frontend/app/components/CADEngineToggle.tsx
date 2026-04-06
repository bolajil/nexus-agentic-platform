'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export type CADEngine = 'freecad' | 'zoo';

interface CADEngineToggleProps {
  value: CADEngine;
  onChange: (engine: CADEngine) => void;
  disabled?: boolean;
}

interface EngineHealth {
  freecad_available: boolean;
  zoo_api_configured: boolean;
}

export function CADEngineToggle({ value, onChange, disabled }: CADEngineToggleProps) {
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch('/api/cad/health');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (err) {
        console.error('Failed to check CAD health:', err);
      } finally {
        setLoading(false);
      }
    }
    checkHealth();
  }, []);

  const isZoo = value === 'zoo';

  return (
    <div className="p-4 bg-[#1a1a35] rounded-lg border border-[#3a3a5a]">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-200">CAD Engine</span>
          {loading && (
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="inline-block w-3 h-3 border border-slate-600 border-t-indigo-400 rounded-full"
            />
          )}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          isZoo 
            ? 'bg-purple-900/30 text-purple-400 border border-purple-500/20' 
            : 'bg-emerald-900/30 text-emerald-400 border border-emerald-500/20'
        }`}>
          {isZoo ? 'Zoo.dev AI' : 'FreeCAD Local'}
        </span>
      </div>

      <div className="flex gap-2">
        {/* FreeCAD Option */}
        <button
          onClick={() => onChange('freecad')}
          disabled={disabled}
          className={`flex-1 p-3 rounded-lg border transition-all ${
            !isZoo
              ? 'bg-emerald-900/30 border-emerald-500/50 text-emerald-300'
              : 'bg-[#1e1e38] border-[#3a3a5a] text-slate-300 hover:border-[#4a4a6a] hover:text-slate-200'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <div className="flex items-center justify-center gap-2 mb-1">
            <span className="text-lg">🔧</span>
            <span className="font-medium text-sm">FreeCAD</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Local • Free • Parametric
          </div>
          {health && (
            <div className={`mt-2 text-[11px] font-medium ${health.freecad_available ? 'text-emerald-400' : 'text-amber-400'}`}>
              {health.freecad_available ? '● Available' : '○ Not Installed'}
            </div>
          )}
        </button>

        {/* Zoo.dev Option */}
        <button
          onClick={() => onChange('zoo')}
          disabled={disabled}
          className={`flex-1 p-3 rounded-lg border transition-all ${
            isZoo
              ? 'bg-purple-900/30 border-purple-500/50 text-purple-300'
              : 'bg-[#1e1e38] border-[#3a3a5a] text-slate-300 hover:border-[#4a4a6a] hover:text-slate-200'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <div className="flex items-center justify-center gap-2 mb-1">
            <span className="text-lg">🤖</span>
            <span className="font-medium text-sm">Zoo.dev</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Cloud • AI • Text-to-CAD
          </div>
          {health && (
            <div className={`mt-2 text-[11px] font-medium ${health.zoo_api_configured ? 'text-emerald-400' : 'text-amber-400'}`}>
              {health.zoo_api_configured ? '● API Ready' : '○ API Key Missing'}
            </div>
          )}
        </button>
      </div>

      {/* Info text */}
      <div className="mt-3 text-[11px] text-slate-400">
        {isZoo ? (
          <span>Zoo.dev uses AI to generate CAD from natural language. <span className="text-purple-400 font-medium">$0.50/min</span></span>
        ) : (
          <span>FreeCAD generates parametric geometry locally using physics-derived parameters.</span>
        )}
      </div>
    </div>
  );
}

export default CADEngineToggle;
