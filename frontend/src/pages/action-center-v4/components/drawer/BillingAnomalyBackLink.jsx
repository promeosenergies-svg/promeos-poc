import { Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle } from 'lucide-react';

/**
 * PROMEOS — Bill Intelligence P2-B C3 (2026-05-24) :
 * Lien retour Action de litige facture → Anomalie source.
 *
 * Quand une action est créée par `POST /api/billing/sync-actions-from-anomalies`
 * (P1 C4), sa `description` commence par `EXTERNAL_REF: billing_anomaly:{id}`.
 * Ce composant extrait cet ID et propose un CTA pour revenir à l'anomalie.
 *
 * Doctrine : aucun nouveau menu, aucune nouvelle page — re-navigue vers
 * `/bill-intel?anomaly=<id>` (la page consommatrice gère l'ouverture du
 * drawer via le query param).
 */
const _EXTERNAL_REF_RE = /EXTERNAL_REF:\s*billing_anomaly:(\d+)/;

export function BillingAnomalyBackLink({ item }) {
  if (!item) return null;
  // Affiché UNIQUEMENT pour les items domain=facturation (action conformité ne
  // montre pas ce CTA — sécurité doctrinale).
  if (item.domain !== 'facturation') return null;

  const desc = item.description || '';
  const match = desc.match(_EXTERNAL_REF_RE);
  if (!match) return null;

  const anomalyId = match[1];

  return (
    <Link
      to={`/bill-intel?anomaly=${anomalyId}`}
      className="mt-3 mb-2 inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-[12.5px] font-medium transition hover:bg-amber-100"
      style={{
        background: 'var(--sol-attention-bg, #fffbeb)',
        color: 'var(--sol-attention-fg, #b45309)',
        borderColor: 'var(--sol-attention-line, #fcd34d)',
      }}
      aria-label={`Retour à l'anomalie facture numéro ${anomalyId}`}
      data-testid="billing-anomaly-back-link"
    >
      <ArrowLeft size={14} aria-hidden="true" />
      <AlertTriangle size={12} aria-hidden="true" />
      <span>
        Voir l&apos;anomalie facture
        <span className="ml-1 font-mono text-[11px] opacity-75">#{anomalyId}</span>
      </span>
    </Link>
  );
}
