/**
 * PROMEOS — AsyncState (universal loading/empty/error wrapper)
 * Usage:
 *   <AsyncState loading={isLoading} error={error} empty={!data?.length} emptyMessage="Aucun site trouvé">
 *     <MonContenu data={data} />
 *   </AsyncState>
 */
import EmptyState from './EmptyState';
import ErrorState from './ErrorState';

function SkeletonBlock({ lines = 3 }) {
  return (
    <div className="animate-pulse space-y-3 py-8 px-4">
      <div className="h-5 bg-gray-200 rounded w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 bg-gray-100 rounded" style={{ width: `${80 - i * 10}%` }} />
      ))}
      <div className="flex gap-4 mt-4">
        <div className="h-20 bg-gray-100 rounded flex-1" />
        <div className="h-20 bg-gray-100 rounded flex-1" />
        <div className="h-20 bg-gray-100 rounded flex-1" />
      </div>
    </div>
  );
}

export default function AsyncState({
  loading,
  error,
  empty,
  emptyMessage = 'Aucune donnée',
  emptyTitle = 'Rien à afficher',
  emptyCta,
  onEmptyCta,
  onRetry,
  skeletonLines = 3,
  children,
}) {
  if (loading) return <SkeletonBlock lines={skeletonLines} />;

  if (error) {
    const msg = typeof error === 'string' ? error : error?.message || 'Une erreur est survenue';
    const debug =
      typeof error === 'object' ? { status: error?.status, error_code: error?.code } : undefined;
    return <ErrorState title="Erreur" message={msg} onRetry={onRetry} debug={debug} />;
  }

  if (empty) {
    return (
      <EmptyState title={emptyTitle} text={emptyMessage} ctaLabel={emptyCta} onCta={onEmptyCta} />
    );
  }

  return children;
}

export { SkeletonBlock };
