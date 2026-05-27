/**
 * Usage Steering P2 cleanup (2026-05-27, brief C2) — renderer générique
 * partagé pour les signaux de pilotage / insights usages.
 *
 * Extrait depuis PilotageTab.PilotageCard (P1 #318). Permet la
 * réutilisation cross-composant (futur Heatmap drill-down, drawer
 * détail, etc.) sans dupliquer la sémantique d'affichage :
 *   - type de signal (label FR)
 *   - site
 *   - impact € (lecture pure, "—" si null — brief « pas de chiffre menteur »)
 *   - confiance (badge)
 *   - action recommandée
 *   - CTA primaire (créer action) + secondaire (voir la source)
 *
 * Stateless : tout passé en props. L'orchestrateur (PilotageTab) gère
 * le busy/feedback state via les props `busyExternalRef` + `lastResult`.
 *
 * Doctrine §8.1 : 0 calcul métier ; lecture pure des champs BE.
 */
import { ArrowRight, CheckCircle2, AlertCircle, ExternalLink, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

// Mapping FR canonique (cross-composant). Aligné PilotageTab + back-link
// drawer V4 PilotageSourceBackLink — source unique de vérité.
export const INSIGHT_LABEL_FR = {
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
      data-testid="usage-signal-confidence"
    >
      {cfg.label}
    </span>
  );
}

/**
 * @param {object} props
 * @param {object} props.signal — { insight_type, site_id, external_ref,
 *   source_url, label_fr, recommended_action_fr, impact_eur, confidence }
 * @param {(signal) => void} props.onCreateAction — handler CTA primaire
 * @param {string|null} props.busyExternalRef — external_ref en cours
 * @param {object|null} props.lastResult — { external_ref, status: 'created' |
 *   'existing' | 'closed' | 'error' } pour feedback inline
 * @param {string} [props.ctaLabel='Créer l\\'action'] — label CTA primaire
 */
export default function UsageSignalCard({
  signal,
  onCreateAction,
  busyExternalRef,
  lastResult,
  ctaLabel = "Créer l'action",
}) {
  const isBusy = busyExternalRef === signal.external_ref;
  const result = lastResult && lastResult.external_ref === signal.external_ref ? lastResult : null;
  const insightLabel = INSIGHT_LABEL_FR[signal.insight_type] || signal.insight_type;
  const impactDisplay = signal.impact_eur != null ? `${fmt(signal.impact_eur)} €/an` : '—';

  return (
    <article
      className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-2"
      data-testid={`usage-signal-${signal.external_ref}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            {insightLabel}
          </p>
          <p className="mt-0.5 text-sm font-medium text-gray-900">{signal.label_fr}</p>
        </div>
        <ConfidenceBadge value={signal.confidence} />
      </div>

      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-gray-700">
        <dt className="text-gray-500">Site</dt>
        <dd className="font-medium">#{signal.site_id}</dd>
        <dt className="text-gray-500">Impact estimé</dt>
        <dd className="font-medium">{impactDisplay}</dd>
      </dl>

      <p className="text-xs text-gray-600 leading-relaxed">
        <span className="font-medium text-gray-800">Action recommandée :</span>{' '}
        {signal.recommended_action_fr}
      </p>

      {result && result.status === 'created' && (
        <p className="text-xs text-emerald-700 inline-flex items-center gap-1">
          <CheckCircle2 size={12} /> Action créée dans le Centre d&apos;Action.
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
          onClick={() => onCreateAction(signal)}
          disabled={isBusy}
          className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:bg-gray-300"
          data-testid={`usage-signal-cta-${signal.external_ref}`}
        >
          {isBusy ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <ArrowRight size={12} aria-hidden="true" />
          )}
          {ctaLabel}
        </button>
        {signal.source_url && (
          <Link
            to={signal.source_url}
            className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-500 hover:text-gray-800"
          >
            <ExternalLink size={11} /> Voir la source
          </Link>
        )}
      </div>
    </article>
  );
}
