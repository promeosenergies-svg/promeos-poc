/**
 * CostSimulationPortfolioCard — Vue agrégée portefeuille.
 *
 * Affiche la facture prévisionnelle 2026 pour l'ensemble des sites du scope,
 * en consommant l'endpoint portfolio `/api/purchase/cost-simulation/portfolio/{org_id}`
 * au lieu de l'endpoint site-level. Résout VEX-Q2 (EPIC #274) : supprime le
 * hard-link site_id=1 qui exposait 595 MWh Siège HELIOS Paris sur la Vue
 * Exécutive portefeuille.
 *
 * Décomposition en 6 composantes réglementaires agrégées (sum-of-parts) :
 *   Fourniture · TURPE 7 · VNU · Capacité RTE · CBAM · Taxes
 *
 * Sources : Post-ARENH 01/01/2026, TURPE 7 (CRE 2025-78), VNU CRE,
 *           mécanisme capacité centralisé RTE.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, AlertTriangle } from 'lucide-react';
import { getPurchasePortfolioCostSimulation } from '../../services/api/cockpit';
import { useScope } from '../../contexts/ScopeContext';
import { fmtEur } from '../../utils/format';
import { Skeleton, InfoTip } from '../../ui';

const MWH_FMT = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 });
function formatMwh(v) {
  if (v == null) return '—';
  return MWH_FMT.format(v);
}

// Palette composantes agrégées portefeuille — ordre stable, WCAG AA.
const COMPOSANTES = [
  {
    key: 'fourniture_eur',
    label: 'Fourniture énergie',
    color: 'bg-blue-500',
    tooltip:
      'Prix forward Y+1 × volume annuel × multiplicateur peakload (HP/HC). Part dominante post-ARENH.',
  },
  {
    key: 'turpe_eur',
    label: 'TURPE 7',
    color: 'bg-zinc-500',
    tooltip:
      "Tarif d'utilisation des réseaux publics d'électricité (Enedis+RTE). CRE 2025-78, en vigueur 01/08/2025.",
  },
  {
    key: 'capacite_eur',
    label: 'Capacité RTE',
    color: 'bg-teal-500',
    tooltip:
      'Mécanisme centralisé acheteur unique RTE (enchères Y-4 / Y-1). Démarrage 01/11/2026, Décret 2025-1441 + Arrêté 18/03/2026.',
  },
  {
    key: 'accise_cta_tva_eur',
    label: 'Taxes (accise + CTA + TVA)',
    color: 'bg-violet-500',
    tooltip:
      "Accise sur l'électricité (ex-TICFE) + Contribution Tarifaire d'Acheminement (15% × part fixe TURPE) + TVA 20%.",
  },
];

// Composantes potentiellement inactives (VNU dormant / CBAM non applicable).
const COMPOSANTES_INACTIVE = [
  {
    key: 'vnu_eur',
    label: 'VNU',
    color: 'bg-amber-500',
    tooltip:
      'Versement Nucléaire Universel — dormant si prix marché < seuil CRE. Exposé en lecture via composantes_inactives.',
  },
  {
    key: 'cbam_scope',
    label: 'CBAM',
    color: 'bg-rose-400',
    tooltip:
      "Mécanisme d'Ajustement Carbone aux Frontières (Règlement UE 2023/956) — non applicable si aucun import hors-UE déclaré.",
  },
];

function ComposanteBar({ composanteKey, label, value, total, color, tooltip, isDormant }) {
  const pct = total > 0 && value > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0;
  return (
    <div className="space-y-1" data-testid={`cost-sim-portfolio-composante-${composanteKey}`}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-gray-700 flex items-center gap-1">
          {label}
          {tooltip ? <InfoTip content={tooltip} /> : null}
        </span>
        <span className="font-medium text-gray-900">
          {isDormant ? (
            <span className="text-amber-600 italic text-[10px] font-normal">dormant</span>
          ) : (
            fmtEur(value)
          )}
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CostSimulationPortfolioCard({ year = 2026 }) {
  const navigate = useNavigate();
  const { org } = useScope();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorCode, setErrorCode] = useState(null);

  useEffect(() => {
    if (!org?.id) {
      setLoading(false);
      return undefined;
    }
    let cancel = false;
    setLoading(true);
    setErrorCode(null);
    getPurchasePortfolioCostSimulation(org.id)
      .then((d) => {
        if (!cancel) setData(d);
      })
      .catch((err) => {
        if (cancel) return;
        const status = err?.response?.status ?? err?.status ?? null;
        setErrorCode(status === 404 ? 404 : 500);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [org?.id]);

  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-5"
        data-testid="purchase-cost-simulation-portfolio-card"
      >
        <Skeleton className="h-5 w-64 mb-3" />
        <Skeleton className="h-12 w-48 mb-4" />
        <div className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      </div>
    );
  }

  if (errorCode === 404) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-5"
        data-testid="purchase-cost-simulation-portfolio-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          Facture énergie portefeuille prévisionnelle
        </h3>
        <p className="text-xs text-gray-500">
          Aucun site avec simulation disponible — contactez votre CSM pour activer la projection{' '}
          {year}.
        </p>
      </div>
    );
  }

  if (errorCode === 500 || !data) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-5"
        data-testid="purchase-cost-simulation-portfolio-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          Facture énergie portefeuille prévisionnelle
        </h3>
        <p className="text-xs text-gray-500">
          Simulation temporairement indisponible — réessayez dans quelques instants.
        </p>
      </div>
    );
  }

  // Agrège les composantes sur tous les sites pour les barres
  const siteCount = data.site_count ?? data.sites?.length ?? 0;
  const totalEur = data.total_portfolio_eur ?? 0;

  // Somme des composantes agrégées sur tous les sites retournés
  const composantesAgg = (data.sites ?? []).reduce(
    (acc, s) => {
      const c = s.composantes ?? {};
      acc.fourniture_eur += c.fourniture_eur ?? 0;
      acc.turpe_eur += c.turpe_eur ?? 0;
      acc.capacite_eur += c.capacite_eur ?? 0;
      acc.accise_cta_tva_eur += c.accise_cta_tva_eur ?? 0;
      return acc;
    },
    { fourniture_eur: 0, turpe_eur: 0, capacite_eur: 0, accise_cta_tva_eur: 0 }
  );

  const inactives = data.composantes_inactives ?? {};
  const vnuEur = inactives.vnu_eur ?? 0;
  const cbamEur = inactives.cbam_eur ?? 0;

  const delta = data.delta_vs_2024 ?? {};
  const deltaPct = delta.delta_pct ?? null;
  const deltaIsNegative = deltaPct != null && deltaPct < 0;
  const deltaIsPositive = deltaPct != null && deltaPct > 0;

  // MWh total estimé = somme fourniture / prix moyen forward estimé 68 €/MWh
  // (indicatif pour affichage uniquement — pas de logique métier ici).
  const energieAnnuelleMwh =
    composantesAgg.fourniture_eur > 0 ? Math.round(composantesAgg.fourniture_eur / 68) : null;

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4"
      data-testid="purchase-cost-simulation-portfolio-card"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-800">
              Facture énergie portefeuille prévisionnelle
            </h3>
            <span
              className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
              data-testid="cost-sim-portfolio-badge-post-arenh"
            >
              Post-ARENH · {siteCount} site{siteCount > 1 ? 's' : ''}
              <InfoTip content="Agrégation sum-of-parts des 6 composantes réglementaires sur tous les sites du portefeuille." />
            </span>
          </div>
          <p className="text-[11px] text-gray-500">
            Projection {year}
            {energieAnnuelleMwh != null ? ` · ~${formatMwh(energieAnnuelleMwh)} MWh/an` : ''}
          </p>
        </div>
        {deltaPct != null && (
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-full whitespace-nowrap ${
              deltaIsNegative
                ? 'bg-emerald-50 text-emerald-700'
                : deltaIsPositive
                  ? 'bg-red-50 text-red-700'
                  : 'bg-gray-50 text-gray-600'
            }`}
            aria-label={
              deltaIsNegative
                ? `Baisse de ${Math.abs(deltaPct).toFixed(1)}% vs 2024 (HT énergie)`
                : `Hausse de ${Math.abs(deltaPct).toFixed(1)}% vs 2024 (HT énergie)`
            }
            data-testid="cost-sim-portfolio-delta-badge"
          >
            {deltaIsNegative ? '↓' : deltaIsPositive ? '↑' : '='} {Math.abs(deltaPct).toFixed(1)}%
            <span className="text-[10px] font-normal opacity-80">vs 2024</span>
          </span>
        )}
      </div>

      {/* Hero big number */}
      <div>
        <div
          className="text-3xl font-bold text-indigo-700 leading-tight"
          data-testid="cost-sim-portfolio-total"
        >
          {fmtEur(totalEur)}
        </div>
        <p className="text-[11px] text-gray-500 mt-1">
          Facture totale estimée · {siteCount} site{siteCount > 1 ? 's' : ''} · 6 composantes
          réglementaires
        </p>
      </div>

      {/* Composantes actives */}
      <div className="space-y-2.5">
        {COMPOSANTES.map((c) => (
          <ComposanteBar
            key={c.key}
            composanteKey={c.key}
            label={c.label}
            value={composantesAgg[c.key] ?? 0}
            total={totalEur}
            color={c.color}
            tooltip={c.tooltip}
            isDormant={false}
          />
        ))}
      </div>

      {/* Composantes inactives (VNU dormant + CBAM) */}
      {(vnuEur > 0 || cbamEur > 0) && (
        <details
          className="border-t border-gray-100 pt-3"
          data-testid="cost-sim-portfolio-composantes-inactives"
        >
          <summary className="text-[11px] uppercase tracking-wide text-gray-400 cursor-pointer font-medium list-none hover:text-gray-600">
            + Composantes inactives · {(vnuEur > 0 ? 1 : 0) + (cbamEur > 0 ? 1 : 0)} ligne
            {(vnuEur > 0 ? 1 : 0) + (cbamEur > 0 ? 1 : 0) > 1 ? 's' : ''}
          </summary>
          <div className="mt-2.5 space-y-2.5">
            {vnuEur === 0 && (
              <ComposanteBar
                composanteKey="vnu_eur"
                label={COMPOSANTES_INACTIVE[0].label}
                value={0}
                total={totalEur}
                color={COMPOSANTES_INACTIVE[0].color}
                tooltip={COMPOSANTES_INACTIVE[0].tooltip}
                isDormant={true}
              />
            )}
            {cbamEur === 0 && (
              <ComposanteBar
                composanteKey="cbam_scope"
                label={COMPOSANTES_INACTIVE[1].label}
                value={0}
                total={totalEur}
                color={COMPOSANTES_INACTIVE[1].color}
                tooltip={COMPOSANTES_INACTIVE[1].tooltip}
                isDormant={false}
              />
            )}
          </div>
        </details>
      )}

      {/* CTA */}
      <button
        type="button"
        onClick={() => navigate('/purchase')}
        aria-label="Voir les scénarios d'achat pour le portefeuille"
        className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
        data-testid="cost-sim-portfolio-cta"
      >
        Voir scénarios portefeuille
        <ArrowRight size={12} />
      </button>

      {/* Footer source */}
      <div className="flex items-center justify-between text-[11px] text-gray-600 pt-2 border-t border-gray-100">
        <span className="flex items-center gap-1">
          Source : Post-ARENH + TURPE 7 + capacité RTE (sum-of-parts {siteCount} sites)
          <InfoTip
            content={`Simulation agrégée basée sur ParameterStore versionné. Méthode : ${delta.method ?? 'agg_per_site_baseline'}. Scope : ${delta.scope ?? 'fourniture_ht_energie'}.`}
          />
        </span>
        <span className="text-gray-400">confiance {data.confiance ?? 'indicative'}</span>
      </div>

      {/* Alerte données extrapolées si un forward manque */}
      {data.confiance === 'low' && (
        <div className="flex items-start gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-800">
          <AlertTriangle size={12} className="shrink-0 mt-0.5" aria-hidden="true" />
          <span>Projection extrapolée — prix forward {year} partiellement indisponibles.</span>
        </div>
      )}
    </div>
  );
}
