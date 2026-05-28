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
import { CheckCircle2, Database } from 'lucide-react';

import { getPilotageSummary, syncPilotageAction } from '../../services/api/energy';
import { useToast } from '../../ui/ToastProvider';
// Usage Steering P2 cleanup (2026-05-27, brief C2) — renderer générique
// extrait de PilotageCard (P1 #318) vers UsageSignalCard.jsx. Permet
// réutilisation cross-composant (futur Heatmap drill-down, drawer, etc.)
// sans dupliquer la sémantique d'affichage. INSIGHT_LABEL_FR exporté
// comme source unique de vérité (utilisé aussi par PilotageSourceBackLink
// drawer V4 — voir P1.5 #320).
import UsageSignalCard from './UsageSignalCard';

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
            <UsageSignalCard
              key={action.external_ref}
              signal={action}
              onCreateAction={handleCreate}
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
