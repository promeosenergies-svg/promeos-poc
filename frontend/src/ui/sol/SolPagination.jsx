/**
 * PROMEOS — SolPagination (Lot 2 Phase 1, Pattern B)
 *
 * Pagination dense mono 11px alignée à droite pour les pages Pattern B.
 * Format canonique : « 1–20 sur 142 · page 1 / 8 · ‹ › · 20 par page ▾ ».
 *
 * Props :
 *   - page: number                          — 1-based
 *   - pageSize: number
 *   - total: number
 *   - onPageChange: (newPage: number) => void
 *   - onPageSizeChange?: (newSize: number) => void
 *   - pageSizeOptions?: number[]            — default [20, 50, 100]
 *
 * Rend null si total <= pageSize ET onPageSizeChange absent
 * (pas de pagination utile sur une seule page).
 */
import React from 'react';

const NBSP = '\u00a0';

export default function SolPagination({
  page = 1,
  pageSize = 20,
  total = 0,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [20, 50, 100],
}) {
  const maxPage = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);

  if (total <= pageSize && !onPageSizeChange) return null;

  const canPrev = page > 1;
  const canNext = page < maxPage;

  return (
    <nav
      aria-label="Pagination"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 14,
        padding: '8px 4px',
        fontFamily: 'var(--sol-font-mono)',
        fontSize: 11,
        color: 'var(--sol-ink-500)',
      }}
    >
      <span>
        {start}
        {NBSP}–{NBSP}
        {end} sur {total}
      </span>
      <span aria-hidden="true" style={{ color: 'var(--sol-ink-300)' }}>
        ·
      </span>
      <span>
        page {page}
        {NBSP}/{NBSP}
        {maxPage}
      </span>
      <div style={{ display: 'inline-flex', gap: 6 }}>
        <button
          type="button"
          aria-label="Page précédente"
          disabled={!canPrev}
          onClick={() => canPrev && onPageChange?.(page - 1)}
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 11,
            padding: '2px 10px',
            border: '1px solid var(--sol-ink-200)',
            background: 'var(--sol-bg-paper)',
            borderRadius: 4,
            color: canPrev ? 'var(--sol-ink-900)' : 'var(--sol-ink-300)',
            cursor: canPrev ? 'pointer' : 'not-allowed',
          }}
        >
          ‹
        </button>
        <button
          type="button"
          aria-label="Page suivante"
          disabled={!canNext}
          onClick={() => canNext && onPageChange?.(page + 1)}
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 11,
            padding: '2px 10px',
            border: '1px solid var(--sol-ink-200)',
            background: 'var(--sol-bg-paper)',
            borderRadius: 4,
            color: canNext ? 'var(--sol-ink-900)' : 'var(--sol-ink-300)',
            cursor: canNext ? 'pointer' : 'not-allowed',
          }}
        >
          ›
        </button>
      </div>
      {onPageSizeChange && (
        <>
          <span aria-hidden="true" style={{ color: 'var(--sol-ink-300)' }}>
            ·
          </span>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              aria-label="Taille de page"
              style={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 11,
                padding: '2px 6px',
                border: '1px solid var(--sol-ink-200)',
                background: 'var(--sol-bg-paper)',
                borderRadius: 4,
                color: 'var(--sol-ink-900)',
                cursor: 'pointer',
              }}
            >
              {pageSizeOptions.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <span>par page</span>
          </label>
        </>
      )}
    </nav>
  );
}
