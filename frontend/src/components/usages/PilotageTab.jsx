/**
 * Usage Steering P1 (2026-05-27) — 4ᵉ onglet « Pilotage des usages »
 * de /usages. Consomme /api/usages/pilotage-summary (contrat figé P0
 * #317) et permet de créer des actions dans Centre d'Action V4 via
 * /api/usages/pilotage/sync-action (idempotent external_ref).
 *
 * Brief P1 :
 *   - Aucun nouveau menu, aucun /usage-steering.
 *   - Aucun calcul métier FE (lecture pure des champs BE).
 *   - 3 priorités maximum visibles above the fold.
 *   - EmptyState « Aucune dérive prioritaire détectée aujourd'hui. »
 *   - Mode expert : source, formule, période, confiance.
 *   - Pas de jargon Flex / NEBCO / AOFD en surface client.
 */
import { useEffect, useState, useCallback } from 'react';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Database,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { getPilotageSummary, syncPilotageAction } from '../../services/api/energy';
import { useToast } from '../../ui/ToastProvider';

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

// Brief : libellés FR clairs sans jargon Flex (NEBCO / AOFD bannis surface
// client). Les types techniques BE sont mappés vers du langage métier.
const INSIGHT_LABEL = {
  hors_horaires: 'Consommation hors horaires',
  base_load: 'Talon de nuit / week-end',
  pointe: 'Pic de puissance',
  derive: 'Dérive de consommation',
  data_gap: 'Lacune de données',
};

const CONFIDENCE_BADGE = {
  high: { label: 'Fiable', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  medium: { label: 'À confirmer', bg: 'bg-amber-50 text-amber-700 border-amber-200' },
  low: { label: 'À fiabiliser', bg: 'bg-gray-100 text-gray-600 border-gray-200' },
};

function ConfidenceBadge({ value }) {
  const cfg = CONFIDENCE_BADGE[value] || CONFIDENCE_BADGE.low;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium border ${cfg.bg}`}
      data-testid="pilotage-card-confidence"
    >
      {cfg.label}
    </span>
  );
}

function PilotageCard({ action, onCreate, busyExternalRef, lastResult }) {
  const isBusy = busyExternalRef === action.external_ref;
  const result = lastResult && lastResult.external_ref === action.external_ref ? lastResult : null;
  const insightLabel = INSIGHT_LABEL[action.insight_type] || action.insight_type;
  // Impact € fiable seulement si BE l'a estimé ; sinon affichage `—`
  // (brief « pas de chiffre menteur »).
  const impactDisplay = action.impact_eur != null ? `${fmt(action.impact_eur)} €/an` : '—';

  return (
    <article
      className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-2"
      data-testid={`pilotage-card-${action.external_ref}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            {insightLabel}
          </p>
          <p className="mt-0.5 text-sm font-medium text-gray-900">{action.label_fr}</p>
        </div>
        <ConfidenceBadge value={action.confidence} />
      </div>

      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-gray-700">
        <dt className="text-gray-500">Site</dt>
        <dd className="font-medium">#{action.site_id}</dd>
        <dt className="text-gray-500">Impact estimé</dt>
        <dd className="font-medium">{impactDisplay}</dd>
      </dl>

      <p className="text-xs text-gray-600 leading-relaxed">
        <span className="font-medium text-gray-800">Action recommandée :</span>{' '}
        {action.recommended_action_fr}
      </p>

      {result && result.status === 'created' && (
        <p className="text-xs text-emerald-700 inline-flex items-center gap-1">
          <CheckCircle2 size={12} /> Action créée dans le Centre d'Action.
        </p>
      )}
      {result && result.status === 'existing' && (
        <p className="text-xs text-amber-700 inline-flex items-center gap-1">
          <CheckCircle2 size={12} /> Cette action existe déjà (idempotente).
        </p>
      )}
      {result && result.status === 'closed' && (
        <p className="text-xs text-gray-600 inline-flex items-center gap-1">
          <AlertCircle size={12} /> Action clôturée — non recréée.
        </p>
      )}

      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={() => onCreate(action)}
          disabled={isBusy}
          className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:bg-gray-300"
          data-testid={`pilotage-card-cta-${action.external_ref}`}
        >
          {isBusy ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <ArrowRight size={12} aria-hidden="true" />
          )}
          Créer l'action
        </button>
        <Link
          to={action.source_url}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-500 hover:text-gray-800"
        >
          <ExternalLink size={11} /> Voir la source
        </Link>
      </div>
    </article>
  );
}

function ExpertDetails({ summary }) {
  const meta = summary?.metadata;
  const dq = summary?.data_quality;
  if (!meta) return null;
  return (
    <details className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs">
      <summary className="cursor-pointer font-medium text-gray-700">
        Détails expert (source, période, confiance)
      </summary>
      <dl className="mt-2 grid grid-cols-[150px_1fr] gap-y-1">
        <dt className="text-gray-500">Périmètre</dt>
        <dd className="text-gray-800">
          {meta.site_count} site{(meta.site_count || 0) > 1 ? 's' : ''}
        </dd>
        <dt className="text-gray-500">Calculé le</dt>
        <dd className="text-gray-800">{meta.computed_at}</dd>
        <dt className="text-gray-500">Insights bruts</dt>
        <dd className="text-gray-800">{dq?.total_insights ?? '—'}</dd>
        <dt className="text-gray-500">Données complètes</dt>
        <dd className="text-gray-800">
          {dq?.score_pct != null ? `${dq.score_pct} %` : '—'} (confiance {dq?.confidence || '—'})
        </dd>
        <dt className="text-gray-500">Contrat de vérité</dt>
        <dd className="text-gray-800">{meta.truth_contract_note}</dd>
      </dl>
    </details>
  );
}

export default function PilotageTab({ scope }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyRef, setBusyRef] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const { toast } = useToast();

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getPilotageSummary({
      entityId: scope?.entityId,
      portefeuilleId: scope?.portefeuilleId,
      siteId: scope?.siteId,
      archetypeCode: scope?.archetypeCode,
    })
      .then((data) => setSummary(data))
      .catch((e) => setError(e?.message || 'Erreur de chargement Pilotage'))
      .finally(() => setLoading(false));
  }, [scope?.entityId, scope?.portefeuilleId, scope?.siteId, scope?.archetypeCode]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = useCallback(
    async (action) => {
      setBusyRef(action.external_ref);
      try {
        const res = await syncPilotageAction({
          insight_type: action.insight_type,
          site_id: action.site_id,
          usage_id: action.usage_id ?? null,
          external_ref: action.external_ref,
          source_url: action.source_url,
          label_fr: action.label_fr,
          recommended_action_fr: action.recommended_action_fr,
          impact_eur: action.impact_eur ?? null,
          severity: action.severity ?? 'medium',
        });
        const status = res?.created ? 'created' : 'existing';
        setLastResult({ external_ref: action.external_ref, status });
        toast(
          status === 'created'
            ? "Action créée dans le Centre d'Action."
            : 'Cette action existe déjà.',
          status === 'created' ? 'success' : 'info'
        );
      } catch (e) {
        const isClosed = e?.response?.status === 409;
        setLastResult({
          external_ref: action.external_ref,
          status: isClosed ? 'closed' : 'error',
        });
        toast(
          isClosed
            ? 'Action déjà clôturée — non recréée.'
            : "Impossible de créer l'action. Vérifier le Centre d'Action.",
          isClosed ? 'info' : 'error'
        );
      } finally {
        setBusyRef(null);
      }
    },
    [toast]
  );

  if (loading) {
    return (
      <div className="p-8 text-center text-sm text-gray-500" data-testid="pilotage-tab-loading">
        Chargement du pilotage…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="m-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        data-testid="pilotage-tab-error"
      >
        Impossible de charger les pilotages.{' '}
        <button onClick={load} className="underline">
          Réessayer
        </button>
      </div>
    );
  }

  const allCandidates = summary?.action_candidates || [];
  // Brief P1 C4 : 3 priorités maximum visibles above the fold.
  const top3 = allCandidates.slice(0, 3);
  const dq = summary?.data_quality || {};
  const isAllDataGap =
    allCandidates.length > 0 && allCandidates.every((a) => a.insight_type === 'data_gap');

  return (
    <section className="px-7 py-6 space-y-4" data-testid="pilotage-tab">
      <header className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Pilotage des usages</h2>
        <span className="text-xs text-gray-500">
          {allCandidates.length} signal{allCandidates.length > 1 ? 's' : ''} cross-brique détecté
          {allCandidates.length > 1 ? 's' : ''}
        </span>
      </header>

      {isAllDataGap && (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
          data-testid="pilotage-tab-data-gap"
          role="status"
        >
          <Database size={14} className="inline mr-1.5" aria-hidden="true" />
          <strong>Données à compléter pour fiabiliser le pilotage.</strong> Les signaux remontés
          concernent uniquement des lacunes de mesure ; complétez la collecte (compteurs, courbes de
          charge) pour permettre un vrai pilotage.
        </div>
      )}

      {top3.length === 0 && !isAllDataGap ? (
        <div
          className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-6 text-sm text-emerald-900 text-center"
          data-testid="pilotage-tab-empty"
        >
          <CheckCircle2 size={20} className="inline mb-1 text-emerald-600" aria-hidden="true" />
          <p className="font-medium">Aucune dérive prioritaire détectée aujourd'hui.</p>
          <p className="mt-1 text-xs text-emerald-800/80">
            Continuez à surveiller les usages dans les onglets Évolution et Baseline.
          </p>
        </div>
      ) : top3.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {top3.map((action) => (
            <PilotageCard
              key={action.external_ref}
              action={action}
              onCreate={handleCreate}
              busyExternalRef={busyRef}
              lastResult={lastResult}
            />
          ))}
        </div>
      ) : null}

      {allCandidates.length > 3 && (
        <p className="text-xs text-gray-500">
          {allCandidates.length - 3} autre{allCandidates.length - 3 > 1 ? 's' : ''} signal
          {allCandidates.length - 3 > 1 ? 'aux' : ''} dans le Centre d'Action V4.
        </p>
      )}

      <ExpertDetails summary={summary} />
    </section>
  );
}
