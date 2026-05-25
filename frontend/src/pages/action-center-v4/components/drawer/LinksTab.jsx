import { ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

import EmptyState from '../../../../ui/EmptyState';
import ErrorState from '../../../../ui/ErrorState';
import Skeleton from '../../../../ui/Skeleton';

import { useActionCenterV4Links } from '../../../../hooks/v4';
import { TAB_COPY } from '../../constants';
import { LinkItem } from './LinkItem';

const LIMIT = 20;

/**
 * M2-5.3.B — Onglet Liens du drawer (read-only, lazy).
 *
 * Action Center V4 P0 fix (2026-05-25) — accepte `sourceUrl` pour rendre
 * un CTA primaire « Voir la source » au-dessus de la liste ActionLink.
 * Permet au DAF/EM/Auditeur de revenir en 1 clic à l'anomalie facture
 * (`/bill-intel?anomaly=X`), à l'obligation conformité (`/conformite?
 * regulation=Y`) ou au site patrimoine sans parser la description
 * (audit deep §6 P0-4).
 */
export function LinksTab({ itemId, sourceUrl }) {
  const { data, loading, error, refetch } = useActionCenterV4Links(itemId, {
    offset: 0,
    limit: LIMIT,
  });

  // CTA « Voir la source » top-level rendu dès qu'on a un source_url valide
  // (pointant vers un hub canonique). Ne dépend pas du chargement des liens
  // ActionLink — c'est l'info la plus directe pour l'utilisateur.
  const sourceCta = sourceUrl ? (
    <Link
      to={sourceUrl}
      className="mb-3 inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
      data-testid="links-source-cta"
    >
      <ExternalLink size={14} aria-hidden="true" />
      Voir la source
    </Link>
  ) : null;

  if (loading) return <Skeleton rows={3} />;

  if (error) {
    return (
      <>
        {sourceCta}
        <ErrorState
          title={TAB_COPY.linksErrorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      </>
    );
  }

  const links = data?.items || [];

  if (links.length === 0) {
    return (
      <>
        {sourceCta}
        <EmptyState
          variant="empty"
          title={TAB_COPY.linksEmptyTitle}
          text={TAB_COPY.linksEmptyText}
        />
      </>
    );
  }

  return (
    <>
      {sourceCta}
      <ol className="space-y-2">
        {links.map((link) => (
          <li key={link.id}>
            <LinkItem link={link} />
          </li>
        ))}
      </ol>
    </>
  );
}
