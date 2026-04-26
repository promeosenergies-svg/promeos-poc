/**
 * SolPageFooter — Source · Confiance · Mis à jour
 *
 * Composant invariant grammaire éditoriale Sol §5.
 * Affiché en bas de chaque page Sol pour matérialiser la crédibilité B2B.
 *
 * Doctrine §5 :
 *   « FOOTER : SOURCE · CONFIANCE · MIS À JOUR »
 *
 * Source-guards : aucune logique métier ici. Tout vient backend
 * via `provenance` envelope du endpoint /api/pages/{page_key}/briefing.
 *
 * Cf. ADR-001 grammaire Sol industrialisée.
 */
import { Info } from 'lucide-react';

const CONFIDENCE_LABELS = Object.freeze({
  high: { label: 'haute', cls: 'text-emerald-700' },
  medium: { label: 'moyenne', cls: 'text-amber-700' },
  low: { label: 'faible', cls: 'text-red-700' },
});

function formatRelativeTime(updatedAt) {
  if (!updatedAt) return '—';
  try {
    const ts = new Date(updatedAt).getTime();
    if (Number.isNaN(ts)) return '—';
    const diffMs = Date.now() - ts;
    const minutes = Math.floor(diffMs / 60_000);
    if (minutes < 1) return "à l'instant";
    if (minutes < 60) return `il y a ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `il y a ${hours} h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `il y a ${days} j`;
    return new Date(updatedAt).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '—';
  }
}

export default function SolPageFooter({
  source,
  confidence = 'medium',
  updatedAt,
  methodologyUrl,
  className = '',
}) {
  const confCfg = CONFIDENCE_LABELS[confidence] ?? CONFIDENCE_LABELS.medium;
  const updatedLabel = formatRelativeTime(updatedAt);

  return (
    <footer
      data-testid="sol-page-footer"
      className={`mt-6 pt-3 border-t border-[var(--sol-line)] flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[var(--sol-ink-500)] ${className}`}
    >
      {source && (
        <span>
          <span className="font-mono uppercase tracking-wider text-[10px] text-[var(--sol-ink-400)] mr-1">
            Source
          </span>
          <span>{source}</span>
        </span>
      )}
      <span>
        <span className="font-mono uppercase tracking-wider text-[10px] text-[var(--sol-ink-400)] mr-1">
          Confiance
        </span>
        <span className={`font-medium ${confCfg.cls}`}>{confCfg.label}</span>
      </span>
      <span>
        <span className="font-mono uppercase tracking-wider text-[10px] text-[var(--sol-ink-400)] mr-1">
          Mis à jour
        </span>
        <span>{updatedLabel}</span>
      </span>
      {methodologyUrl && (
        <a
          href={methodologyUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[var(--sol-ink-500)] hover:text-[var(--sol-ink-700)] underline-offset-2 hover:underline"
        >
          <Info size={11} aria-hidden="true" />
          Méthodologie
        </a>
      )}
    </footer>
  );
}
