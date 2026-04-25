/**
 * PROMEOS — SolExpertGridFull (Lot 2 Phase 1, Pattern B)
 *
 * Superset du SolExpertGrid existant : ajoute selectable checkbox +
 * onRowClick drawer trigger + loading state + empty state narratif +
 * render custom par colonne + highlightColumn pour ton visuel accentué.
 *
 * Reste compatible avec la shape SolExpertGrid legacy (colonnes key/label,
 * rows key/cells). Ne casse pas les appelants Phase 3 showcase.
 *
 * Props :
 *   - columns: Array<{
 *       id|key: string,                     — compat (both accepted)
 *       label: string,
 *       sortable?: boolean,
 *       width?: string|number,
 *       align?: 'left'|'right'|'center',
 *       render?: (value, row) => ReactNode  — render custom cellule
 *     }>
 *   - rows: Array<{
 *       id|key: string|number,
 *       cells: { [col_id]: any },
 *       tone?: 'calme'|'attention'|'afaire'|'succes'|'refuse', — ligne
 *       onClick?: () => void                — override row.onClick
 *     }>
 *   - sortBy?: { column: string, direction: 'asc'|'desc' }
 *   - onSort?: (columnId) => void
 *   - selectable?: boolean                  — col 1 = checkbox
 *   - selectedIds?: Set<string|number>
 *   - onSelectionChange?: (newSet) => void
 *   - onRowClick?: (row) => void            — prioritaire vs row.onClick
 *   - emptyState?: { title, message, action?: { label, onClick } }
 *   - loading?: boolean
 *   - highlightColumn?: string              — col_id dont la cellule s'accentue
 */
import React from 'react';

const TONE_BG = {
  calme: 'var(--sol-calme-bg)',
  attention: 'var(--sol-attention-bg)',
  afaire: 'var(--sol-afaire-bg)',
  succes: 'var(--sol-succes-bg)',
  refuse: 'var(--sol-refuse-bg)',
};

export default function SolExpertGridFull({
  columns = [],
  rows = [],
  sortBy = null,
  onSort,
  selectable = false,
  selectedIds,
  onSelectionChange,
  onRowClick,
  emptyState,
  loading = false,
  highlightColumn,
}) {
  const colId = (c) => c.id ?? c.key;
  const rowId = (r) => r.id ?? r.key;

  const toggleSelect = (id) => {
    if (!onSelectionChange) return;
    const next = new Set(selectedIds || []);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  };

  const toggleAll = () => {
    if (!onSelectionChange) return;
    const allIds = rows.map(rowId);
    const allSelected = allIds.every((id) => selectedIds?.has(id));
    onSelectionChange(allSelected ? new Set() : new Set(allIds));
  };

  if (loading) {
    return (
      <p
        style={{
          fontFamily: 'var(--sol-font-body)',
          fontSize: 13,
          color: 'var(--sol-ink-500)',
          fontStyle: 'italic',
          padding: '24px 0',
          margin: 0,
          textAlign: 'center',
        }}
      >
        Chargement en cours…
      </p>
    );
  }

  if (rows.length === 0 && emptyState) {
    return (
      <div
        role="status"
        style={{
          padding: '28px 24px',
          background: 'var(--sol-bg-paper)',
          border: '1px dashed var(--sol-ink-200)',
          borderRadius: 6,
          textAlign: 'center',
        }}
      >
        <p
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: 0,
            marginBottom: 6,
          }}
        >
          {emptyState.title}
        </p>
        <p
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 13,
            color: 'var(--sol-ink-500)',
            margin: 0,
            marginBottom: emptyState.action ? 14 : 0,
            lineHeight: 1.45,
          }}
        >
          {emptyState.message}
        </p>
        {emptyState.action && (
          <button
            type="button"
            onClick={emptyState.action.onClick}
            className="sol-btn sol-btn--secondary"
          >
            {emptyState.action.label}
          </button>
        )}
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        className="sol-expert-grid-full"
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 12,
          fontVariantNumeric: 'tabular-nums',
          fontFamily: 'var(--sol-font-mono)',
        }}
      >
        <thead>
          <tr>
            {selectable && (
              <th
                style={{
                  width: 32,
                  padding: '8px 10px',
                  borderBottom: '1px solid var(--sol-rule)',
                  textAlign: 'center',
                }}
              >
                <input
                  type="checkbox"
                  aria-label="Tout sélectionner"
                  checked={rows.length > 0 && rows.every((r) => selectedIds?.has(rowId(r)))}
                  onChange={toggleAll}
                />
              </th>
            )}
            {columns.map((col) => {
              const id = colId(col);
              const active = sortBy?.column === id;
              const dir = active ? sortBy.direction : null;
              const canSort = col.sortable && onSort;
              const ariaSort = canSort
                ? active
                  ? dir === 'asc'
                    ? 'ascending'
                    : 'descending'
                  : 'none'
                : undefined;
              return (
                <th
                  key={id}
                  scope="col"
                  aria-sort={ariaSort}
                  onClick={canSort ? () => onSort(id) : undefined}
                  style={{
                    textAlign: col.align || 'left',
                    width: col.width,
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    fontWeight: 600,
                    color: active ? 'var(--sol-ink-900)' : 'var(--sol-ink-500)',
                    borderBottom: '1px solid var(--sol-rule)',
                    padding: '8px 10px',
                    cursor: canSort ? 'pointer' : 'default',
                    WebkitUserSelect: 'none',
                    userSelect: 'none',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {col.label}
                  {active && <span style={{ marginLeft: 4 }}>{dir === 'asc' ? '▲' : '▼'}</span>}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const rid = rowId(row);
            const clickable = Boolean(onRowClick || row.onClick);
            const handleClick = clickable
              ? () => (onRowClick ? onRowClick(row) : row.onClick?.())
              : undefined;
            const isSelected = selectedIds?.has(rid);
            const toneBg = row.tone ? TONE_BG[row.tone] : null;
            return (
              <tr
                key={rid}
                onClick={handleClick}
                style={{
                  cursor: clickable ? 'pointer' : 'default',
                  background: isSelected ? 'var(--sol-calme-bg)' : toneBg || 'transparent',
                  transition: 'background-color 120ms ease',
                }}
                onMouseEnter={(e) => {
                  if (clickable && !isSelected && !toneBg) {
                    e.currentTarget.style.background = 'var(--sol-ink-100)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected && !toneBg) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                {selectable && (
                  <td
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      padding: '8px 10px',
                      borderBottom: '1px solid var(--sol-ink-200)',
                      textAlign: 'center',
                    }}
                  >
                    <input
                      type="checkbox"
                      aria-label={`Sélectionner ligne ${rid}`}
                      checked={Boolean(isSelected)}
                      onChange={() => toggleSelect(rid)}
                    />
                  </td>
                )}
                {columns.map((col) => {
                  const cid = colId(col);
                  const value = row.cells?.[cid];
                  const rendered = col.render ? col.render(value, row) : value;
                  const isHi = highlightColumn === cid;
                  return (
                    <td
                      key={cid}
                      style={{
                        padding: '8px 10px',
                        textAlign: col.align || 'left',
                        borderBottom: '1px solid var(--sol-ink-200)',
                        color: isHi ? 'var(--sol-ink-900)' : 'var(--sol-ink-700)',
                        fontWeight: isHi ? 600 : 400,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {rendered ?? '—'}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
