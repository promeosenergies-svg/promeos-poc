/**
 * PROMEOS — ImpactDecisionPanel
 * Panneau "Impact & Décision" pour le Cockpit.
 * 3 KPIs agrégés (€) + 1 recommandation actionnable.
 *
 * Données:
 *   - kpis (scopedSites)   → risque conformité (déjà calculé)
 *   - getBillingSummary()   → surcoût facture + base opportunité
 * Aucune nouvelle API créée.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert, Receipt, TrendingUp, ArrowRight, Info, Loader2, Zap,
} from 'lucide-react';
import { Card, CardBody, Badge, Tooltip, Button } from '../../ui';
import { KPI_ACCENTS } from '../../ui/colorTokens';
import { fmtEur } from '../../utils/format';
import { getBillingSummary } from '../../services/api';
import { computeImpactKpis, computeRecommendation } from '../../models/impactDecisionModel';
import { computeActionableLevers } from '../../models/leverEngineModel';

// ── KPI tile (inline — small enough) ─────────────────────────────────────────

function ImpactKpiTile({ icon: Icon, label, value, available, tooltip, accent, onClick, ariaLabel, dominant, subLabel }) {
  const a = KPI_ACCENTS[accent] || KPI_ACCENTS.neutral;
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      onClick={onClick}
      aria-label={ariaLabel}
      data-dominant={dominant || undefined}
      className={`flex items-start gap-3 p-4 rounded-lg border text-left w-full${
        dominant ? ` ${a.border} ${a.tintBg} shadow-sm` : ' border-gray-200 bg-white'
      }${onClick ? ' cursor-pointer hover:shadow-sm transition-all' : ''}`}
      {...(onClick ? { type: 'button' } : {})}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${a.iconBg}`}>
        <Icon size={18} className={a.iconText} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wide">{label}</p>
          {dominant && (
            <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded ${a.iconBg} ${a.tintText}`}>
              Prioritaire
            </span>
          )}
          {tooltip && (
            <Tooltip content={tooltip}>
              <Info size={12} className="text-gray-400 cursor-help" />
            </Tooltip>
          )}
        </div>
        <p className="text-lg font-bold text-gray-900 mt-0.5">
          {available ? fmtEur(value) : '—'}
        </p>
        {available && subLabel && (
          <p className="text-[11px] text-gray-400 mt-0.5">{subLabel}</p>
        )}
        {!available && (
          <Badge variant="neutral" size="xs">Données manquantes</Badge>
        )}
      </div>
    </Tag>
  );
}

// ── Main Panel ───────────────────────────────────────────────────────────────

export default function ImpactDecisionPanel({ kpis }) {
  const navigate = useNavigate();
  const [billingSummary, setBillingSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getBillingSummary()
      .then((data) => { if (!cancelled) setBillingSummary(data); })
      .catch(() => { if (!cancelled) setBillingSummary({}); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const impact = useMemo(
    () => computeImpactKpis(kpis, billingSummary || {}),
    [kpis, billingSummary],
  );

  const reco = useMemo(
    () => computeRecommendation(impact, kpis),
    [impact, kpis],
  );

  // V33 — Levier Engine
  const levers = useMemo(
    () => computeActionableLevers({ kpis, billingSummary: billingSummary || {} }),
    [kpis, billingSummary],
  );

  const handleDrillDown = (type) => {
    if (type === 'risque') navigate('/patrimoine?filter=risque');
    if (type === 'surcout') navigate('/factures?filter=anomalies');
    if (type === 'optimisation') navigate('/consommations?filter=energivores');
  };

  // V32 — KPI dominant (max € parmi les 3)
  const dominantKey = useMemo(() => {
    const { risqueConformite, surcoutFacture, opportuniteOptim } = impact;
    const max = Math.max(risqueConformite, surcoutFacture, opportuniteOptim);
    if (max === 0) return null;
    if (risqueConformite >= surcoutFacture && risqueConformite >= opportuniteOptim) return 'risque';
    if (surcoutFacture >= opportuniteOptim) return 'surcout';
    return 'optimisation';
  }, [impact]);

  // V32 — Compteurs contextuels (données déjà en scope, aucune nouvelle API)
  const subLabels = useMemo(() => {
    const rs = (kpis?.nonConformes ?? 0) + (kpis?.aRisque ?? 0);
    const ac = billingSummary?.invoices_with_anomalies ?? billingSummary?.total_insights ?? null;
    return {
      risque: rs > 0 ? `${rs} site${rs > 1 ? 's' : ''} concerné${rs > 1 ? 's' : ''}` : null,
      surcout: ac != null && ac > 0 ? `${ac} facture${ac > 1 ? 's' : ''} impactée${ac > 1 ? 's' : ''}` : null,
      optimisation: null,
    };
  }, [kpis, billingSummary]);

  // Loading state
  if (loading) {
    return (
      <Card>
        <CardBody className="flex items-center justify-center gap-2 py-8 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Chargement Impact & Décision…</span>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-3" data-testid="impact-decision-panel">
      {/* ── Titre section ── */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Impact & Décision
        </h3>
        <Tooltip content="Calculs V1 — règles déterministes basées sur vos données réelles">
          <span className="text-[10px] text-gray-400 border border-gray-200 rounded px-1.5 py-0.5 cursor-help">
            V1
          </span>
        </Tooltip>
      </div>

      {/* ── 3 KPIs ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <ImpactKpiTile
          icon={ShieldAlert}
          label="Risque conformité"
          value={impact.risqueConformite}
          available={impact.risqueAvailable}
          tooltip="Somme des risques financiers des sites non conformes ou à risque dans le périmètre actif"
          accent="risque"
          onClick={() => handleDrillDown('risque')}
          ariaLabel="Voir les sites à risque conformité"
          dominant={dominantKey === 'risque'}
          subLabel={subLabels.risque}
        />
        <ImpactKpiTile
          icon={Receipt}
          label="Surcoût facture"
          value={impact.surcoutFacture}
          available={impact.surcoutAvailable}
          tooltip="Total des pertes identifiées par le moteur d'audit facture (shadow billing)"
          accent="alertes"
          onClick={() => handleDrillDown('surcout')}
          ariaLabel="Voir les anomalies de facturation"
          dominant={dominantKey === 'surcout'}
          subLabel={subLabels.surcout}
        />
        <ImpactKpiTile
          icon={TrendingUp}
          label="Opportunité optimisation"
          value={impact.opportuniteOptim}
          available={impact.optimAvailable}
          tooltip="Heuristique V1 : 1 % du montant facturé total — affiné à mesure que les données s'enrichissent"
          accent="conformite"
          onClick={() => handleDrillDown('optimisation')}
          ariaLabel="Voir les sites énergivores"
          dominant={dominantKey === 'optimisation'}
          subLabel={subLabels.optimisation}
        />
      </div>

      {/* ── Leviers activables V33 ── */}
      <div className="rounded-lg border border-gray-200 bg-gray-50/50 p-4" data-testid="levers-section">
        {levers.totalLevers > 0 ? (
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <Zap size={16} className="text-amber-500 shrink-0" />
                <p className="text-sm font-semibold text-gray-900">
                  {levers.totalLevers} levier{levers.totalLevers > 1 ? 's' : ''} activable{levers.totalLevers > 1 ? 's' : ''}
                </p>
              </div>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                {[
                  levers.leversByType.conformite > 0 && `${levers.leversByType.conformite} conformit\u00e9`,
                  levers.leversByType.facturation > 0 && `${levers.leversByType.facturation} facturation`,
                  levers.leversByType.optimisation > 0 && `${levers.leversByType.optimisation} optimisation`,
                ].filter(Boolean).join(' \u2022 ')}
              </p>
            </div>
            <Button
              size="sm"
              variant="secondary"
              className="shrink-0"
              onClick={() => navigate('/command-center?filter=leviers')}
            >
              Voir les leviers <ArrowRight size={14} />
            </Button>
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-1">Aucun levier d\u00e9tect\u00e9 (V1)</p>
        )}
      </div>

      {/* ── Recommandation prioritaire ── */}
      <div className="rounded-lg border border-indigo-200/60 bg-indigo-50/30 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-gray-900">{reco.titre}</p>
            <ul className="mt-2 space-y-1">
              {reco.bullets.map((b, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                  <span className="mt-1 w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                  {b}
                </li>
              ))}
            </ul>
          </div>
          <Button
            size="sm"
            className="shrink-0 mt-1"
            onClick={() => navigate(reco.ctaPath)}
          >
            {reco.cta} <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
}
