/**
 * PROMEOS — DataReadinessBadge (Step 3.1)
 * Premium popover badge in AppShell header.
 * Click opens a popover with level + top 3 reasons + CTA.
 */
import { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, ArrowRight, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { useDemo } from '../contexts/DemoContext';
import useDataReadiness from '../hooks/useDataReadiness';
import Badge from '../ui/Badge';
import {
  loadReadinessSnapshot,
  saveReadinessSnapshot,
  computeReadinessTrend,
} from '../models/dataReadinessModel';

const SEVERITY_DOT = {
  critical: 'bg-red-500',
  high: 'bg-amber-500',
  medium: 'bg-blue-400',
};

const LEVEL_BG = {
  GREEN: 'bg-green-50 border-green-200',
  AMBER: 'bg-amber-50 border-amber-200',
  RED: 'bg-red-50 border-red-200',
};

const LEVEL_TITLE_COLOR = {
  GREEN: 'text-green-800',
  AMBER: 'text-amber-800',
  RED: 'text-red-800',
};

export default function DataReadinessBadge() {
  const navigate = useNavigate();
  const { org, scope, scopedSites } = useScope();
  const { demoEnabled } = useDemo();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const kpis = useMemo(() => {
    const sites = scopedSites;
    const total = sites.length;
    const conformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = sites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = sites.filter((s) => s.statut_conformite === 'a_risque').length;
    const couvertureDonnees =
      total > 0 ? Math.round((sites.filter((s) => s.conso_kwh_an > 0).length / total) * 100) : 0;
    return { total, conformes, nonConformes, aRisque, couvertureDonnees };
  }, [scopedSites]);

  const { readinessState, loading } = useDataReadiness(kpis, { demoEnabled });

  // Snapshot scope
  const snapshotScope = useMemo(
    () => ({
      orgId: org?.id,
      scopeType: scope?.portefeuilleId ? 'pf' : scope?.siteId ? 'site' : 'all',
      scopeId: scope?.portefeuilleId || scope?.siteId || 0,
    }),
    [org?.id, scope?.portefeuilleId, scope?.siteId]
  );

  // Trend
  const trend = useMemo(() => {
    if (!readinessState) return { delta: 0, labelFR: '' };
    const prev = loadReadinessSnapshot(snapshotScope);
    return computeReadinessTrend(readinessState, prev);
  }, [readinessState, snapshotScope]);

  // Save snapshot on readiness change
  useEffect(() => {
    if (readinessState && !loading) {
      saveReadinessSnapshot(readinessState, snapshotScope);
    }
  }, [readinessState, loading, snapshotScope]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open]);

  if (!kpis.total || loading || !readinessState) return null;

  return (
    <div ref={ref} className="relative" data-testid="data-readiness-badge">
      {/* Badge trigger */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-slate-100 transition-colors"
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Database size={14} className="text-slate-400" />
        <Badge status={readinessState.badgeStatus}>{readinessState.badgeLabel}</Badge>
        {trend.delta !== 0 && (
          <span
            className={`text-[10px] font-medium ${trend.delta > 0 ? 'text-green-600' : 'text-red-500'}`}
          >
            {trend.delta > 0 ? (
              <TrendingUp size={10} className="inline" />
            ) : (
              <TrendingDown size={10} className="inline" />
            )}
          </span>
        )}
      </button>

      {/* Popover */}
      {open && (
        <div
          className="absolute top-full left-0 mt-2 w-80 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden"
          role="dialog"
          aria-label="Statut des données"
          data-testid="readiness-popover"
        >
          {/* Header */}
          <div className={`px-4 py-3 border-b ${LEVEL_BG[readinessState.level]}`}>
            <div className="flex items-center justify-between">
              <h3 className={`text-sm font-bold ${LEVEL_TITLE_COLOR[readinessState.level]}`}>
                Données : {readinessState.badgeLabel}
              </h3>
              {trend.labelFR && (
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${trend.delta > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}
                >
                  {trend.labelFR}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 mt-0.5">{readinessState.subtitle}</p>
          </div>

          {/* Reasons (max 3) */}
          {readinessState.reasons.length > 0 && (
            <div className="px-3 py-2 space-y-1" data-testid="readiness-reasons">
              {readinessState.reasons.map((r) => (
                <button
                  key={r.id}
                  onClick={() => {
                    navigate(r.path);
                    setOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-50 transition text-left"
                >
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${SEVERITY_DOT[r.severity] || 'bg-gray-400'}`}
                  />
                  <span className="text-xs text-gray-700 flex-1 truncate">{r.label}</span>
                  <ArrowRight size={12} className="text-gray-300 shrink-0" />
                </button>
              ))}
              {readinessState.secondaryCta && (
                <button
                  onClick={() => {
                    navigate(readinessState.secondaryCta.to);
                    setOpen(false);
                  }}
                  className="w-full text-center text-[11px] font-medium text-blue-600 hover:text-blue-800 py-1"
                >
                  {readinessState.secondaryCta.label}
                </button>
              )}
            </div>
          )}

          {/* CTA */}
          <div className="px-3 py-2.5 border-t border-gray-100 bg-gray-50/50">
            <button
              onClick={() => {
                navigate(readinessState.primaryCta.to);
                setOpen(false);
              }}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold
                text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              data-testid="readiness-cta"
            >
              {readinessState.level !== 'GREEN' && <AlertTriangle size={12} />}
              {readinessState.level === 'GREEN' ? "Voir l'activation" : 'Corriger maintenant'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
