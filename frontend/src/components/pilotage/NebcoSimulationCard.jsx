/**
 * NebcoSimulationCard - Pilotage Vague 2.
 *
 * Rejeu historique : "voici ce que vous auriez gagne le mois dernier en
 * decalant vos usages flexibles". Preuve chiffree sur CDC reelle + spot
 * ENTSO-E (vs ROI annuel estime de RoiFlexReadyCard).
 *
 * Doctrine wording cote client : jamais "NEBCO" / "flex" / "prix negatif".
 * On parle de "valorisation", "decalage d'usages", "fenetres favorables".
 *
 * Source : Barometre Flex 2026 (RTE/Enedis/GIMELEC) + spot ENTSO-E France.
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, TrendingUp } from 'lucide-react';
import { getNebcoSimulation } from '../../services/api/pilotage';
import { useScope } from '../../contexts/ScopeContext';
import { toSite } from '../../services/routes';
import { fmtEur } from '../../utils/format';
import { Skeleton, InfoTip } from '../../ui';
import { humaniseArchetype, humaniseSiteId } from './archetypeLabels';

// Phase 0.7 (sprint Cockpit dual sol2) : fallback `'retail-001'` retiré.
// Si pas de siteId résolu (scope HELIOS sans site sélectionné), on rend
// un empty state au lieu de leak Hypermarché Montreuil.

// Formatteur Intl force sur Europe/Paris pour afficher la periode de rejeu
// independamment du fuseau navigateur (backend renvoie ISO YYYY-MM-DD).
const PERIODE_FMT = new Intl.DateTimeFormat('fr-FR', {
  timeZone: 'Europe/Paris',
  day: '2-digit',
  month: '2-digit',
});

function formatPeriode(debut, fin) {
  if (!debut || !fin) return '—';
  try {
    return `${PERIODE_FMT.format(new Date(debut))} au ${PERIODE_FMT.format(new Date(fin))}`;
  } catch {
    return `${debut} → ${fin}`;
  }
}

function formatKwhCompact(v) {
  if (!v || v <= 0) return '0 kWh';
  if (v >= 1_000_000)
    return `${(v / 1_000_000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} GWh`;
  if (v >= 1_000) return `${(v / 1_000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} MWh`;
  return `${Math.round(v).toLocaleString('fr-FR')} kWh`;
}

function ComposanteBar({ label, value, total, color, tooltip, testid }) {
  const pct = total > 0 ? Math.max(2, Math.round((Math.abs(value) / total) * 100)) : 0;
  return (
    <div className="space-y-1" data-testid={testid}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-gray-700 flex items-center gap-1">
          {label}
          {tooltip ? <InfoTip content={tooltip} /> : null}
        </span>
        <span className="font-medium text-gray-900">{fmtEur(value)}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function NebcoSimulationCard({ siteId: siteIdProp, periodDays = 30 }) {
  const navigate = useNavigate();
  const { scope, scopedSites } = useScope();

  const resolvedSiteId = String(
    siteIdProp || scope?.siteId || (scopedSites && scopedSites[0]?.id) || ''
  );

  const siteNom = useMemo(() => {
    if (!resolvedSiteId) return null;
    const found = scopedSites?.find((s) => String(s.id) === resolvedSiteId);
    return found?.nom || null;
  }, [scopedSites, resolvedSiteId]);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedDays, setExpandedDays] = useState(periodDays);

  useEffect(() => {
    if (!resolvedSiteId) {
      setLoading(false);
      return;
    }
    let cancel = false;
    setLoading(true);
    setError(null);
    getNebcoSimulation(resolvedSiteId, expandedDays)
      .then((d) => {
        if (!cancel) setData(d);
      })
      .catch((err) => {
        if (!cancel) {
          // Distinguer 404 (CDC non seedée) de 500/timeout (backend down) :
          // sans ça, un backend KO afficherait "CDC non seedée" qui est un
          // mensonge et décrédibilise la démo.
          const status = err?.response?.status ?? err?.status ?? 0;
          setError(status === 404 ? 'cdc_missing' : 'backend_error');
        }
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [resolvedSiteId, expandedDays]);

  // Empty state propre quand aucun site dans le scope HELIOS courant
  if (!resolvedSiteId && !loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4 text-sm text-gray-500"
        data-testid="pilotage-nebco-card-empty"
      >
        Sélectionnez un site du portefeuille pour estimer le revenu d'effacement.
      </div>
    );
  }

  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-nebco-card"
      >
        <Skeleton className="h-5 w-48 mb-3" />
        <Skeleton className="h-12 w-40 mb-4" />
        <Skeleton className="h-24 rounded" />
      </div>
    );
  }

  if (error || !data) {
    const message =
      error === 'backend_error'
        ? 'Rejeu temporairement indisponible — réessayez dans quelques instants.'
        : 'CDC du site non seedée — contactez votre CSM pour activer le rejeu sur données réelles.';
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-nebco-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">Gain simulé — rejeu historique</h3>
        <p className="text-xs text-gray-500">{message}</p>
      </div>
    );
  }

  const {
    gain_simule_eur,
    kwh_decales_total,
    n_fenetres_favorables,
    spread_moyen_eur_mwh,
    composantes = {},
    hypotheses = {},
    periode_debut,
    periode_fin,
    confiance,
    source,
  } = data;

  const gainTotal = Number(gain_simule_eur || 0);
  const gainSpread = Number(composantes.gain_spread_eur || 0);
  const compensation = Number(composantes.compensation_fournisseur_eur || 0);
  const net = Number(composantes.net_eur || gainTotal);

  // Echelle commune pour les 3 barres (la plus grande composante = 100%).
  const maxComposante = Math.max(Math.abs(gainSpread), Math.abs(compensation), Math.abs(net), 1);

  const hasData = kwh_decales_total > 0 || n_fenetres_favorables > 0;
  const ctaLabel = scope?.siteId ? 'Explorer le détail' : 'Explorer un site démo';
  const ctaTarget = scope?.siteId ? toSite(scope.siteId) : '/sites';

  // Etat "aucune fenetre detectee" : on propose d'elargir a 90 j si pas deja fait.
  if (!hasData) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
        data-testid="pilotage-nebco-card"
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-gray-800">Gain simulé — rejeu historique</h3>
            <p className="text-[11px] text-gray-500 mt-0.5">
              Rejeu du {formatPeriode(periode_debut, periode_fin)}
            </p>
          </div>
          <span className="inline-flex items-center bg-emerald-50 text-emerald-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap">
            Preuve chiffrée
          </span>
        </div>
        <p className="text-xs text-gray-500">Aucune fenêtre favorable détectée sur la période.</p>
        {expandedDays < 90 && (
          <button
            type="button"
            onClick={() => setExpandedDays(90)}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 hover:text-indigo-900 hover:underline self-start"
            data-testid="pilotage-nebco-expand"
          >
            Élargir à 90 j
            <ArrowRight size={12} />
          </button>
        )}
        <div className="text-[10px] text-gray-400 mt-auto pt-1 border-t border-gray-100">
          Source : {source || 'Baromètre Flex 2026 · CDC Enedis + spot ENTSO-E'}
        </div>
      </div>
    );
  }

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
      data-testid="pilotage-nebco-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-emerald-600" />
            Gain simulé — rejeu historique
          </h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            {siteNom || humaniseSiteId(resolvedSiteId)} · archétype{' '}
            {humaniseArchetype(hypotheses.archetype)}
          </p>
        </div>
        <span
          className="inline-flex items-center bg-emerald-50 text-emerald-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
          title="Rejeu sur courbe de charge réelle et prix spot ENTSO-E"
        >
          Preuve chiffrée
        </span>
      </div>

      {/* Hero big number */}
      <div>
        <div
          className="text-3xl font-bold text-emerald-700 leading-none"
          data-testid="pilotage-nebco-hero"
        >
          {fmtEur(gainTotal)}
        </div>
        <div className="text-[11px] text-gray-500 mt-1">
          Gain simulé sur les {expandedDays} derniers jours en décalant vos usages pilotables
        </div>
      </div>

      {/* Composantes */}
      <div className="space-y-2.5">
        <ComposanteBar
          label="Valorisation spread"
          value={gainSpread}
          total={maxComposante}
          color="bg-amber-500"
          tooltip="Différentiel entre heures évitées (prix hauts) et heures visées (prix bas / parfois négatifs) × kWh décalés."
          testid="pilotage-nebco-gain-spread"
        />
        <ComposanteBar
          label="Compensation fournisseur"
          value={-compensation}
          total={maxComposante}
          color="bg-gray-500"
          tooltip="Part réglementaire reversée à votre fournisseur d'énergie historique sur les volumes déplacés."
          testid="pilotage-nebco-compensation"
        />
        <ComposanteBar
          label="Net pour votre site"
          value={net}
          total={maxComposante}
          color="bg-emerald-500"
          tooltip="Gain réel conservé après compensation : c'est le chiffre qui compte pour votre P&L."
          testid="pilotage-nebco-net"
        />
      </div>

      {/* Micro-stats */}
      <div
        className="text-[11px] text-gray-600 flex flex-wrap items-center gap-x-2 gap-y-1"
        data-testid="pilotage-nebco-microstats"
      >
        <span>
          <strong className="text-gray-900">{n_fenetres_favorables || 0}</strong> fenêtre
          {(n_fenetres_favorables || 0) > 1 ? 's' : ''} détectée
          {(n_fenetres_favorables || 0) > 1 ? 's' : ''}
        </span>
        <span aria-hidden="true">·</span>
        <span>
          <strong className="text-gray-900">{formatKwhCompact(kwh_decales_total)}</strong>{' '}
          décalables
        </span>
        <span aria-hidden="true">·</span>
        <span>
          spread moyen{' '}
          <strong className="text-gray-900">{Math.round(spread_moyen_eur_mwh || 0)} €/MWh</strong>
        </span>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-gray-500">
          Rejeu du {formatPeriode(periode_debut, periode_fin)}
        </span>
        <span className="text-[10px] text-gray-400 lowercase">
          confiance {confiance || 'indicative'}
        </span>
      </div>

      <button
        type="button"
        onClick={() => navigate(ctaTarget)}
        className="mt-1 inline-flex items-center justify-between gap-1 text-xs font-medium text-indigo-700 hover:text-indigo-900 hover:underline"
        data-testid="pilotage-nebco-cta"
      >
        <span>{ctaLabel}</span>
        <ArrowRight size={12} />
      </button>

      <div className="text-[10px] text-gray-400 mt-auto pt-1 border-t border-gray-100 flex items-center gap-1">
        Source : {source || 'Baromètre Flex 2026 · CDC Enedis + spot ENTSO-E'}
        <InfoTip content="Calcul sur courbe de charge réelle (SGE) et prix spot historiques France ENTSO-E. Taux décalable calibré par archétype NAF." />
      </div>
    </div>
  );
}
