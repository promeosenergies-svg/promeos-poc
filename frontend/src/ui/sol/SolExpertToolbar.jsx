/**
 * PROMEOS — SolExpertToolbar (Lot 2 Phase 1, Pattern B)
 *
 * Toolbar horizontale sticky pour les pages Pattern B (liste drillable).
 * Mono 11.5px, background paper, structure :
 *
 *   [search input à gauche]
 *   [filtres pills cliquables au centre]
 *   [selection pills + actions masse à droite]
 *
 * Filtres = pills cliquables avec options en dropdown simple HTML
 * <select> pour éviter un composant dropdown custom lourd. Réduit les
 * dépendances et garantit accessibilité native.
 *
 * Props :
 *   - filters: Array<{
 *       id: string,
 *       label: string,
 *       value: string|null,
 *       options: Array<{ value, label }>
 *     }>
 *   - activeFilters: { [id]: value }          — state courant (lu pour l'UI)
 *   - onFilterChange: (id, value) => void
 *   - searchPlaceholder?: string
 *   - searchValue?: string
 *   - onSearchChange?: (value) => void
 *   - selection?: { count, total }
 *   - selectionActions?: Array<{ label, onClick, variant?: 'primary'|'secondary' }>
 *   - activeFilterCount?: number              — source chip "N filtres actifs"
 */
import React from 'react';

export default function SolExpertToolbar({
  filters = [],
  activeFilters = {},
  onFilterChange,
  searchPlaceholder = 'Rechercher…',
  searchValue = '',
  onSearchChange,
  selection,
  selectionActions = [],
  activeFilterCount,
}) {
  const nActive =
    activeFilterCount != null
      ? activeFilterCount
      : Object.values(activeFilters).filter((v) => v != null && v !== '').length;

  return (
    <div
      role="toolbar"
      aria-label="Filtres et sélection"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
        padding: '10px 14px',
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 6,
        fontFamily: 'var(--sol-font-mono)',
        fontSize: 11.5,
        color: 'var(--sol-ink-700)',
      }}
    >
      {onSearchChange && (
        <input
          type="search"
          aria-label={searchPlaceholder}
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            flex: '0 1 220px',
            padding: '6px 10px',
            background: 'var(--sol-bg-paper)',
            border: '1px solid var(--sol-ink-200)',
            borderRadius: 4,
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 11.5,
            color: 'var(--sol-ink-900)',
            outline: 'none',
          }}
        />
      )}

      {filters.length > 0 && (
        <div
          style={{
            display: 'flex',
            gap: 8,
            flexWrap: 'wrap',
            alignItems: 'center',
            flex: '1 1 auto',
          }}
        >
          {filters.map((f) => {
            const current = activeFilters[f.id] ?? f.value ?? '';
            const isActive = current !== '' && current != null;
            return (
              <label
                key={f.id}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '4px 10px',
                  borderRadius: 999,
                  border: `1px solid ${isActive ? 'var(--sol-calme-fg)' : 'var(--sol-ink-200)'}`,
                  background: isActive ? 'var(--sol-calme-bg)' : 'transparent',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  fontSize: 10.5,
                  fontWeight: 600,
                  color: isActive ? 'var(--sol-calme-fg)' : 'var(--sol-ink-500)',
                  cursor: 'pointer',
                }}
              >
                <span aria-hidden="true">{f.label}</span>
                <select
                  value={current}
                  onChange={(e) => onFilterChange?.(f.id, e.target.value)}
                  aria-label={`Filtrer par ${f.label}`}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 10.5,
                    fontWeight: 600,
                    color: 'inherit',
                    outline: 'none',
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  <option value="">tous</option>
                  {(f.options || []).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
            );
          })}
          {nActive > 0 && (
            <span
              aria-label={`${nActive} filtres actifs`}
              style={{
                marginLeft: 4,
                color: 'var(--sol-calme-fg)',
                fontWeight: 600,
              }}
            >
              ● {nActive}
              {'\u00a0'}actif{nActive > 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {selection && selection.count > 0 && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 10,
            padding: '4px 10px',
            background: 'var(--sol-attention-bg)',
            color: 'var(--sol-attention-fg)',
            borderRadius: 4,
            fontWeight: 600,
          }}
        >
          Sélection {selection.count}
          {'\u00a0/\u00a0'}
          {selection.total ?? '—'}
          {selectionActions.map((a, i) => (
            <button
              key={`${a.label}-${i}`}
              type="button"
              onClick={a.onClick}
              className={`sol-btn sol-btn--${a.variant || 'secondary'}`}
              style={{ fontSize: 11, padding: '4px 10px' }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
