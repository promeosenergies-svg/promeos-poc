import { Link } from 'react-router-dom';
import { ArrowLeft, Sliders } from 'lucide-react';

/**
 * PROMEOS — Usage Steering P1.5 (2026-05-27) :
 * Lien retour Action d'optimisation énergétique → 4ᵉ onglet Pilotage des
 * usages source.
 *
 * Quand une action est créée par `POST /api/usages/pilotage/sync-action`
 * (P1 #318), elle expose :
 *   - `domain = 'optimisation'`
 *   - `external_ref = 'pilotage:{insight_type}:site:{id}[:date]'`
 *   - `source_url = '/usages?tab=pilotage&site={id}'`
 *
 * Ce composant détecte le pattern pilotage et propose un CTA pour revenir
 * au 4ᵉ onglet Pilotage des usages du site concerné. Pattern identique à
 * BillingAnomalyBackLink — cohérence cross-brique.
 *
 * Doctrine : aucun nouveau menu, aucune nouvelle page — re-navigue vers
 * `source_url` directement (la page consommatrice gère le tab actif +
 * focus site).
 */
const _PILOTAGE_REF_RE = /^pilotage:([a-z_]+):site:(\d+)/;

const _INSIGHT_LABEL_FR = {
  hors_horaires: 'Consommation hors horaires',
  base_load: 'Talon de nuit / week-end',
  pointe: 'Pic de puissance',
  derive: 'Dérive de consommation',
  data_gap: 'Lacune de données',
};

export function PilotageSourceBackLink({ item }) {
  if (!item) return null;
  // Affiché uniquement pour les items domain=optimisation issus du
  // pilotage des usages (external_ref préfixe `pilotage:`).
  if (item.domain !== 'optimisation') return null;
  const ref = item.external_ref || '';
  const match = ref.match(_PILOTAGE_REF_RE);
  if (!match) return null;

  const insightType = match[1];
  const siteId = match[2];
  const insightLabel = _INSIGHT_LABEL_FR[insightType] || insightType;
  // source_url exposée par le BE depuis P1 — fallback construction si absent.
  const href = item.source_url || `/usages?tab=pilotage&site=${siteId}`;

  return (
    <Link
      to={href}
      className="mt-3 mb-2 inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-[12.5px] font-medium transition hover:bg-emerald-100"
      style={{
        background: 'var(--sol-success-bg, #ecfdf5)',
        color: 'var(--sol-success-fg, #047857)',
        borderColor: 'var(--sol-success-line, #6ee7b7)',
      }}
      aria-label={`Voir la source dans Pilotage des usages — site ${siteId} (${insightLabel})`}
      data-testid="pilotage-source-back-link"
    >
      <ArrowLeft size={14} aria-hidden="true" />
      <Sliders size={12} aria-hidden="true" />
      <span>
        Source : Pilotage des usages
        <span className="ml-1 text-[11px] opacity-75">
          — site #{siteId} · {insightLabel}
        </span>
      </span>
    </Link>
  );
}
