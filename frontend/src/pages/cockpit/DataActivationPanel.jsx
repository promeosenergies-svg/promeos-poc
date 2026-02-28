/**
 * PROMEOS — DataActivationPanel V37
 * Section cockpit compacte : barre de progression + statut par brique.
 * Self-contained (fetch propre, meme pattern qu'ImpactDecisionPanel).
 *
 * Props: { kpis }
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database, CheckCircle2, Circle, ArrowRight, Loader2,
} from 'lucide-react';
import { Card, CardBody, InfoTip, Button, Progress } from '../../ui';
import { TOOLTIPS } from '../../ui/tooltips';
import { getBillingSummary, getPurchaseRenewals, patrimoineContracts } from '../../services/api';
import { normalizePurchaseSignals } from '../../models/purchaseSignalsContract';
import { buildActivationChecklist } from '../../models/dataActivationModel';

export default function DataActivationPanel({ kpis }) {
  const navigate = useNavigate();
  const [billingSummary, setBillingSummary] = useState(null);
  const [purchaseSignals, setPurchaseSignals] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getBillingSummary().catch(() => ({})),
      getPurchaseRenewals().catch(() => ({ total: 0, renewals: [] })),
      patrimoineContracts().catch(() => ({ total: 0, contracts: [] })),
    ]).then(([billing, renewals, contracts]) => {
      if (!cancelled) {
        setBillingSummary(billing);
        setPurchaseSignals(normalizePurchaseSignals({
          renewals,
          contracts,
          totalSites: kpis?.total ?? 0,
        }));
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [kpis?.total]);

  const activation = useMemo(
    () => buildActivationChecklist({
      kpis: kpis || {},
      billingSummary: billingSummary || {},
      purchaseSignals,
    }),
    [kpis, billingSummary, purchaseSignals],
  );

  if (loading) {
    return (
      <Card>
        <CardBody className="flex items-center justify-center gap-2 py-6 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Chargement activation…</span>
        </CardBody>
      </Card>
    );
  }

  const allActive = activation.activatedCount === activation.totalDimensions;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4" data-testid="data-activation-panel">
      {/* En-tete */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Database size={16} className="text-gray-500 shrink-0" />
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            Activation des données
          </h4>
          <InfoTip content={TOOLTIPS.executive.activationDonnees} />
        </div>
        <span className="text-xs font-medium text-gray-500">
          {activation.activatedCount}/{activation.totalDimensions} briques
        </span>
      </div>

      {/* Barre de progression */}
      <Progress value={activation.overallCoverage} size="sm" color="blue" />
      <p className="text-[10px] text-gray-400 mt-1">{activation.overallCoverage}{'\u202f'}% couverture moyenne</p>

      {/* Badges par dimension */}
      <div className="flex flex-wrap gap-2 mt-3">
        {activation.dimensions.map((dim) => (
          <div key={dim.key} className="flex items-center gap-1">
            {dim.available
              ? <CheckCircle2 size={12} className="text-emerald-500" />
              : <Circle size={12} className="text-gray-300" />}
            <span className={`text-[11px] ${dim.available ? 'text-gray-600' : 'text-gray-400'}`}>
              {dim.label}
            </span>
            {dim.available && dim.detail && (
              <span className="text-[10px] text-gray-400">({dim.detail})</span>
            )}
          </div>
        ))}
      </div>

      {/* Etat succes ou CTA */}
      {allActive ? (
        <p className="mt-3 text-xs text-emerald-600 font-medium">
          Toutes les briques sont actives
        </p>
      ) : (
        <>
          {activation.nextAction && (
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
              <p className="text-xs text-gray-500">{activation.nextAction.ctaLabel}</p>
              <Button
                size="xs"
                variant="secondary"
                className="shrink-0 text-xs"
                onClick={() => navigate(activation.nextAction.ctaPath)}
                aria-label={`Compl\u00e9ter : ${activation.nextAction.label}`}
              >
                Compléter <ArrowRight size={12} />
              </Button>
            </div>
          )}
          <button
            onClick={() => navigate('/activation')}
            className="mt-2 text-[11px] text-blue-500 hover:underline"
            aria-label="Voir le d\u00e9tail de l'activation des donn\u00e9es"
          >
            Voir le détail →
          </button>
        </>
      )}
    </div>
  );
}
