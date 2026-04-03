import { ChevronLeft, ChevronRight } from 'lucide-react';

export const PAGE_SIZE_OPTIONS = [20, 50, 100];

export default function Pagination({ page, pageSize, total, onChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm">
      <div className="flex items-center gap-2 text-gray-500">
        <span>{total > 0 ? `${from}\u2013${to} sur ${total}` : 'Aucun résultat'}</span>
        {onPageSizeChange && (
          <>
            <span className="text-gray-300">&middot;</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="border border-gray-200 rounded px-1.5 py-0.5 text-xs bg-white"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n} / page
                </option>
              ))}
            </select>
          </>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label="Page précédente"
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="px-3 text-gray-700 font-medium tabular-nums">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Page suivante"
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
