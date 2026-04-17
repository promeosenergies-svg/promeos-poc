/**
 * CostSimulationCard - Sprint Achat post-ARENH MVP.
 *
 * Répond à la question d'un acheteur B2B en 2026 :
 * "Quelle sera ma facture énergie 2026+ post-ARENH ?"
 *
 * Décomposition en 6 composantes réglementaires :
 *   1. Fourniture énergie (prix forward Y+1)
 *   2. TURPE 7 (distribution + transport)
 *   3. VNU (volume nucléaire universel — peut être dormant si prix < seuil)
 *   4. Capacité RTE (mécanisme centralisé nov. 2026)
 *   5. CBAM (scope importations carbone — souvent non applicable)
 *   6. Taxes (accise + CTA + TVA)
 *
 * Sources : Post-ARENH 01/01/2026, TURPE 7 (CRE 2025-78), VNU CRE,
 *           mécanisme capacité centralisé RTE.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, AlertTriangle } from 'lucide-react';
import { getCostSimulation2026 } from '../../services/api/purchase';
import { useScope } from '../../contexts/ScopeContext';
import { toSite } from '../../services/routes';
import { fmtEur } from '../../utils/format';
import { Skeleton, InfoTip } from '../../ui';

// Intl forcé Europe/Paris pour les nombres (cohérent avec autres cartes pilotage)
const MWH_FMT = new Intl.NumberFormat('fr-FR', {
  maximumFractionDigits: 0,
});

function formatMwh(v) {
  if (v == null) return '—';
  return MWH_FMT.format(v);
}

// Palette des composantes — ordre d'affichage stable
const COMPOSANTES = [
  {
    key: 'fourniture_eur',
    label: 'Fourniture énergie',
    color: 'bg-blue-500',
    tooltip: 'Prix forward Y+1 × volume annuel. Part dominante post-ARENH.',
  },
  {
    key: 'turpe_eur',
    label: 'TURPE 7',
    color: 'bg-gray-500',
    tooltip: "Tarif d'utilisation des réseaux publics d'électricité (CRE 2025-78, août 2025).",
  },
  {
    key: 'vnu_eur',
    label: 'VNU',
    color: 'bg-amber-500',
    tooltip:
      "Volume Nucléaire Universel — s'active uniquement si prix marché > seuil CRE 78 €/MWh.",
  },
  {
    key: 'capacite_eur',
    label: 'Capacité RTE',
    color: 'bg-orange-500',
    tooltip: 'Mécanisme centralisé (enchères PL-4 / PL-1), nov. 2026.',
  },
  {
    key: 'cbam_scope',
    label: 'CBAM',
    color: 'bg-slate-400',
    tooltip: 'Ajustement carbone aux frontières — applicable aux imports de scope couvert.',
  },
  {
    key: 'accise_cta_tva_eur',
    label: 'Taxes (accise + CTA + TVA)',
    color: 'bg-indigo-400',
    tooltip: "Accise sur l'électricité + Contribution Tarifaire d'Acheminement + TVA 20%.",
  },
];

function ComposanteBar({
  composanteKey,
  label,
  value,
  total,
  color,
  tooltip,
  isDormant,
  isNotApplicable,
}) {
  const pct = total > 0 && value > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0;
  // Fix audit : data-testid stable via `composanteKey` (pas dérivé du label FR
  // qui contient parenthèses/+ instables pour Playwright).
  return (
    <div className="space-y-1" data-testid={`cost-sim-composante-${composanteKey}`}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-gray-700 flex items-center gap-1">
          {label}
          {tooltip ? <InfoTip content={tooltip} /> : null}
        </span>
        <span className="font-medium text-gray-900">
          {isDormant ? (
            <span
              className="text-amber-600 italic text-[10px] font-normal"
              aria-label={`${label} — dormant, non activé car prix marché sous le seuil CRE`}
            >
              dormant
            </span>
          ) : isNotApplicable ? (
            <span
              className="text-gray-400 italic text-[10px] font-normal"
              aria-label={`${label} — non applicable à la consommation électrique directe`}
            >
              non applicable
            </span>
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

export default function CostSimulationCard({ siteId: siteIdProp, year = 2026 }) {
  const navigate = useNavigate();
  const { scope } = useScope();

  const resolvedSiteId = siteIdProp || scope?.siteId || null;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorCode, setErrorCode] = useState(null); // 404 | 500 | null

  useEffect(() => {
    if (!resolvedSiteId) {
      setLoading(false);
      return undefined;
    }
    let cancel = false;
    setLoading(true);
    setErrorCode(null);
    getCostSimulation2026(resolvedSiteId, year)
      .then((d) => {
        if (!cancel) setData(d);
      })
      .catch((err) => {
        if (cancel) return;
        // Distinction 404 (site sans simulation) vs 500/timeout (indispo)
        const status = err?.response?.status ?? err?.status ?? null;
        setErrorCode(status === 404 ? 404 : 500);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [resolvedSiteId, year]);

  const handleCta = () => {
    navigate(resolvedSiteId ? toSite(resolvedSiteId, { tab: 'achats' }) : '/achat-energie');
  };

  // ── Loading ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-5"
        data-testid="purchase-cost-simulation-card"
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

  // ── Error states (404 vs 500 distincts) ──────────────────────────────
  if (errorCode === 404) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-5"
        data-testid="purchase-cost-simulation-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">Facture énergie post-ARENH</h3>
        <p className="text-xs text-gray-500">
          Site sans simulation — contactez votre CSM pour activer la projection {year}.
        </p>
      </div>
    );
  }

  if (errorCode === 500 || !data) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-5"
        data-testid="purchase-cost-simulation-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">Facture énergie post-ARENH</h3>
        <p className="text-xs text-gray-500">
          Simulation temporairement indisponible — réessayez dans quelques instants.
        </p>
      </div>
    );
  }

  // ── Success state ────────────────────────────────────────────────────
  const {
    facture_totale_eur: total,
    energie_annuelle_mwh: mwh,
    composantes = {},
    hypotheses = {},
    delta_vs_2024_pct: deltaPct,
    confiance,
    source,
  } = data;

  const vnuStatut = hypotheses?.vnu_statut || 'dormant';
  const vnuActif = vnuStatut === 'actif';
  const vnuSeuil = hypotheses?.vnu_seuil_active_eur_mwh ?? 78;

  const deltaIsNegative = deltaPct != null && deltaPct < 0;
  const deltaIsPositive = deltaPct != null && deltaPct > 0;

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4"
      data-testid="purchase-cost-simulation-card"
    >
      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-800">Facture énergie prévisionnelle</h3>
            <span
              className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
              data-testid="cost-sim-badge-post-arenh"
            >
              Post-ARENH
            </span>
          </div>
          <p className="text-[11px] text-gray-500">
            Projection {year} · {formatMwh(mwh)} MWh/an
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
            data-testid="cost-sim-delta-badge"
          >
            {deltaIsNegative ? '↓' : deltaIsPositive ? '↑' : '='} {Math.abs(deltaPct).toFixed(1)}%
            <span className="text-[10px] font-normal opacity-80">vs 2024</span>
          </span>
        )}
      </div>

      {/* ── Hero big number ──────────────────────────────────────────── */}
      <div>
        <div
          className="text-3xl font-bold text-indigo-700 leading-tight"
          data-testid="cost-sim-total"
        >
          {fmtEur(total)}
        </div>
        <p className="text-[11px] text-gray-500 mt-1">
          Facture totale estimée · 6 composantes réglementaires
        </p>
      </div>

      {/* ── Alert VNU actif (conditionnel) ──────────────────────────── */}
      {vnuActif && (
        <div
          className="flex items-start gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-800"
          data-testid="cost-sim-vnu-alert"
        >
          <AlertTriangle size={12} className="shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            <strong>VNU actif</strong> — prix marché &gt; seuil CRE {vnuSeuil} €/MWh. Composante
            complémentaire activée.
          </span>
        </div>
      )}

      {/* ── 6 composantes empilées ───────────────────────────────────── */}
      <div className="space-y-2.5">
        {COMPOSANTES.map((c) => {
          const value = composantes[c.key] ?? 0;
          const isVnu = c.key === 'vnu_eur';
          const isCbam = c.key === 'cbam_scope';
          return (
            <ComposanteBar
              key={c.key}
              composanteKey={c.key}
              label={c.label}
              value={value}
              total={total}
              color={c.color}
              tooltip={c.tooltip}
              isDormant={isVnu && !vnuActif}
              isNotApplicable={isCbam && (value == null || value === 0)}
            />
          );
        })}
      </div>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={handleCta}
        aria-label="Voir les scénarios d'achat pour ce site"
        className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
        data-testid="cost-sim-cta-scenarios"
      >
        Voir scénarios
        <ArrowRight size={12} />
      </button>

      {/* ── Footer source ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-[10px] text-gray-400 pt-2 border-t border-gray-100">
        <span className="flex items-center gap-1">
          Source : {source || 'Post-ARENH + TURPE 7 + VNU + capacité RTE'}
          <InfoTip content="Simulation basée sur paramètres réglementaires versionnés (ParameterStore) et prix forward marché." />
        </span>
        {confiance && <span>confiance {confiance}</span>}
      </div>
    </div>
  );
}
