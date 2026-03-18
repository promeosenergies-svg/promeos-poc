/**
 * ComplianceSummaryBanner — Bandeau contextuel 3 etats (vert/rouge/ambre).
 * Affiche un message actionnable + CTA selon le niveau de conformite.
 */
import { ShieldCheck, ArrowRight, CalendarClock } from 'lucide-react';
import { Button } from '../../ui';
import { getKpiMessage } from '../../services/kpiMessaging';
import { formatDeadline } from './conformiteUtils';

export default function ComplianceSummaryBanner({
  score,
  obligations,
  timeline,
  isExpert,
  navigate,
}) {
  const nextDeadline = timeline?.next_deadline || null;
  const pct = score?.pct ?? 0;
  const nonConformes = score?.non_conformes ?? 0;
  const aRisque = score?.a_risque ?? 0;
  const totalSites = score?.total ?? 0;

  // Determine state: green (>=70 & 0 NC), red (<40 or NC>0), amber (else)
  let state = 'amber';
  if (pct >= 70 && nonConformes === 0) state = 'green';
  else if (pct < 40 || nonConformes > 0) state = 'red';

  const stateConfig = {
    green: {
      bg: 'bg-green-50 border-green-200',
      iconColor: 'text-green-600',
      textColor: 'text-green-800',
      subColor: 'text-green-600',
    },
    amber: {
      bg: 'bg-amber-50 border-amber-200',
      iconColor: 'text-amber-600',
      textColor: 'text-amber-800',
      subColor: 'text-amber-600',
    },
    red: {
      bg: 'bg-red-50 border-red-200',
      iconColor: 'text-red-600',
      textColor: 'text-red-800',
      subColor: 'text-red-600',
    },
  };

  const cfg = stateConfig[state];

  // kpiMessaging for conformite
  const conformiteMsg = getKpiMessage('conformite', pct, {
    totalSites,
    sitesAtRisk: aRisque,
    sitesNonConformes: nonConformes,
  });
  // kpiMessaging for risque
  const risqueMsg = getKpiMessage('risque', score?.total_impact_eur ?? 0, {
    sitesAtRisk: aRisque,
  });

  return (
    <div
      data-testid="compliance-summary-banner"
      data-state={state}
      className={`p-4 border rounded-lg ${cfg.bg}`}
    >
      <div className="flex items-start gap-3">
        <ShieldCheck size={20} className={`${cfg.iconColor} mt-0.5 shrink-0`} />
        <div className="flex-1 min-w-0">
          {/* Main message from kpiMessaging */}
          {conformiteMsg && (
            <p
              className={`text-sm font-medium ${cfg.textColor}`}
              data-testid="kpi-message-conformite"
            >
              {isExpert ? conformiteMsg.expert : conformiteMsg.simple}
            </p>
          )}
          {/* Risque message */}
          {risqueMsg && risqueMsg.severity !== 'ok' && (
            <p className={`text-xs mt-1 ${cfg.subColor}`} data-testid="kpi-message-risque">
              {isExpert ? risqueMsg.expert : risqueMsg.simple}
            </p>
          )}
          {/* Next deadline */}
          {nextDeadline && (
            <p
              className="text-xs mt-1.5 flex items-center gap-1 text-gray-600"
              data-testid="next-deadline"
            >
              <CalendarClock size={12} />
              Prochaine échéance : {nextDeadline.label || nextDeadline.regulation} —{' '}
              {new Date(nextDeadline.deadline).toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
              {nextDeadline.days_remaining != null && (
                <span
                  className={nextDeadline.days_remaining <= 30 ? 'font-semibold text-red-600' : ''}
                >
                  {' '}
                  (dans {nextDeadline.days_remaining} jour
                  {nextDeadline.days_remaining > 1 ? 's' : ''})
                </span>
              )}
            </p>
          )}
        </div>
        {/* CTA buttons */}
        <div className="flex items-center gap-2 shrink-0">
          {state === 'red' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                navigate('/actions');
              }}
              data-testid="cta-plan-action"
            >
              Voir le plan d&apos;action <ArrowRight size={14} />
            </Button>
          )}
          {state === 'amber' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                navigate('/conformite?tab=execution');
              }}
              data-testid="cta-preparer-echeances"
            >
              Préparer les échéances <ArrowRight size={14} />
            </Button>
          )}
        </div>
      </div>

      {/* B2 — Resume executif 1 ligne */}
      {(() => {
        const oblCount = obligations?.length || 0;
        const ncCount = nonConformes;
        const urgentDeadline = nextDeadline?.days_remaining;
        const urgentLabel =
          urgentDeadline != null && urgentDeadline <= 90
            ? `1 échéance sous ${urgentDeadline} jour${urgentDeadline > 1 ? 's' : ''}`
            : null;
        const parts = [
          `${oblCount} obligation${oblCount > 1 ? 's' : ''} active${oblCount > 1 ? 's' : ''}`,
          ncCount > 0 ? `${ncCount} non conforme${ncCount > 1 ? 's' : ''}` : null,
          aRisque > 0 ? `${aRisque} à qualifier` : null,
          urgentLabel,
        ].filter(Boolean);
        if (parts.length === 0 || !isExpert) return null;
        return (
          <p data-testid="executive-summary" className="text-xs text-gray-600 mt-2 font-medium">
            {parts.join(' · ')}
          </p>
        );
      })()}

      {/* B2 — Top 3 urgences */}
      {(() => {
        if (!obligations?.length) return null;
        // Compute urgency: severity x proximity x penalty
        const sevWeight = { critical: 100, high: 70, medium: 40, low: 10 };
        const scored = obligations
          .filter((o) => o.statut !== 'conforme' && o.statut !== 'hors_perimetre')
          .map((o) => {
            const sev = sevWeight[o.severity] || 10;
            const daysLeft = o.echeance
              ? Math.max(0, (new Date(o.echeance) - new Date()) / 86400000)
              : 999;
            const proximity = daysLeft <= 0 ? 100 : daysLeft <= 90 ? 80 : daysLeft <= 365 ? 50 : 20;
            const penalty = (o.findings || []).reduce(
              (s, f) => s + (f.estimated_penalty_eur || 0),
              0
            );
            return {
              ...o,
              _urgency: sev * 0.4 + proximity * 0.4 + Math.min(penalty / 100, 20) * 0.2,
            };
          })
          .sort((a, b) => b._urgency - a._urgency)
          .slice(0, 3);
        if (scored.length === 0) return null;
        return (
          <div
            data-testid="top3-urgences"
            className="mt-3 p-3 bg-white/60 rounded-lg border border-gray-200/50"
          >
            <p className="text-xs font-semibold text-gray-700 uppercase mb-2">
              Top {scored.length} urgence{scored.length > 1 ? 's' : ''}
            </p>
            <div className="space-y-1.5">
              {scored.map((o, i) => (
                <div key={o.id} className="flex items-center gap-2 text-sm">
                  <span className="text-xs font-bold text-gray-400 w-5">{i + 1}</span>
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      o.severity === 'critical'
                        ? 'bg-red-500'
                        : o.severity === 'high'
                          ? 'bg-orange-500'
                          : 'bg-amber-400'
                    }`}
                  />
                  <span className="font-medium text-gray-800 flex-1 truncate">{o.regulation}</span>
                  {o.echeance &&
                    (() => {
                      const dl = formatDeadline(o.echeance, o.statut);
                      return (
                        <span
                          className={`text-xs ${dl.overdue ? 'text-red-600 font-semibold' : 'text-gray-500'}`}
                        >
                          {dl.text}
                        </span>
                      );
                    })()}
                  <span
                    className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      o.statut === 'non_conforme'
                        ? 'bg-red-50 text-red-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}
                  >
                    {o.statut === 'non_conforme' ? 'Non conforme' : 'À qualifier'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
