/**
 * PROMEOS — Data Quality Widget (Cockpit V113)
 * Shows org-level data completeness summary: coverage %, green/amber/red breakdown.
 * Fetches from GET /api/data-quality/completeness?org_id=...
 */
import { useState, useEffect } from 'react';
import { Database, ArrowRight, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useScope } from '../../contexts/ScopeContext';
import { getDataQualityCompleteness, getDataQualityPortfolio } from '../../services/api';
import { Card, CardBody } from '../../ui';
import DataQualityBadge from '../../components/DataQualityBadge';

const STATUS_CONFIG = {
  green: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle, label: 'Complet' },
  amber: { color: 'text-amber-600', bg: 'bg-amber-50', icon: Clock, label: 'Partiel' },
  red: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle, label: 'Manquant' },
};

export default function DataQualityWidget() {
  const { org } = useScope();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [dqPortfolio, setDqPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!org?.id) return;
    setLoading(true);
    Promise.all([
      getDataQualityCompleteness(org.id).catch(() => null),
      getDataQualityPortfolio(org.id).catch(() => null),
    ])
      .then(([completeness, portfolio]) => {
        setData(completeness);
        setDqPortfolio(portfolio);
      })
      .finally(() => setLoading(false));
  }, [org?.id]);

  if (loading) {
    return (
      <Card>
        <CardBody className="flex items-center gap-3 animate-pulse">
          <div className="w-9 h-9 rounded-lg bg-gray-200" />
          <div className="flex-1 space-y-2">
            <div className="h-3 bg-gray-200 rounded w-32" />
            <div className="h-2 bg-gray-100 rounded w-48" />
          </div>
        </CardBody>
      </Card>
    );
  }

  if (!data) return null;

  const { overall_coverage_pct, summary, sites_count } = data;
  const coverageColor =
    overall_coverage_pct >= 80
      ? 'text-emerald-600'
      : overall_coverage_pct >= 50
        ? 'text-amber-600'
        : 'text-red-600';
  const barColor =
    overall_coverage_pct >= 80
      ? 'bg-emerald-500'
      : overall_coverage_pct >= 50
        ? 'bg-amber-500'
        : 'bg-red-500';

  return (
    <Card>
      <CardBody className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
              <Database size={16} className="text-indigo-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Qualité des données</p>
              <p className="text-[10px] text-gray-400">
                {sites_count} site{sites_count > 1 ? 's' : ''} analyses
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {dqPortfolio && <DataQualityBadge score={dqPortfolio.avg_score} size="md" />}
            <span className={`text-xl font-bold ${coverageColor}`}>{overall_coverage_pct}%</span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full ${barColor} rounded-full transition-all duration-500`}
            style={{ width: `${overall_coverage_pct}%` }}
          />
        </div>

        {/* Status breakdown */}
        <div className="flex items-center gap-4">
          {['green', 'amber', 'red'].map((status) => {
            const cfg = STATUS_CONFIG[status];
            const count = summary[status] || 0;
            if (count === 0) return null;
            const Icon = cfg.icon;
            return (
              <div key={status} className={`flex items-center gap-1.5 px-2 py-1 rounded ${cfg.bg}`}>
                <Icon size={12} className={cfg.color} />
                <span className={`text-xs font-medium ${cfg.color}`}>
                  {count} {cfg.label.toLowerCase()}
                </span>
              </div>
            );
          })}
        </div>

        {/* Top issues (first 3 red rows) with CTA */}
        {data.rows &&
          (() => {
            const redRows = data.rows.filter((r) => r.status === 'red').slice(0, 3);
            if (!redRows.length) return null;
            return (
              <div className="space-y-1.5 pt-1">
                {redRows.map((row, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-xs text-gray-600 bg-red-50/50 px-2 py-1 rounded group"
                    title={row.next_step || ''}
                  >
                    <span className="truncate">{row.cause}</span>
                    {row.cta_route ? (
                      <button
                        onClick={() => navigate(row.cta_route)}
                        className="text-red-600 font-medium whitespace-nowrap ml-2 hover:underline"
                      >
                        Corriger
                      </button>
                    ) : row.next_step ? (
                      <span className="text-red-600 font-medium whitespace-nowrap ml-2">
                        {row.next_step}
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
            );
          })()}

        {/* CTA */}
        <button
          onClick={() => navigate('/conformite?tab=donnees')}
          className="flex items-center gap-1 text-xs text-indigo-600 font-medium hover:text-indigo-800 transition pt-1"
        >
          Voir le détail <ArrowRight size={12} />
        </button>
      </CardBody>
    </Card>
  );
}
