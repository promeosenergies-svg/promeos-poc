/**
 * PROMEOS — SolExpertGrid
 * Table dense triable pour mode Expert. Présentation pure : l'appelant
 * fournit columns + rows déjà normalisés.
 *
 * Props :
 *   columns : [{ key, label, align: 'left' | 'right', num: boolean }]
 *   rows    : [{ key, cells: { [colKey]: ReactNode } }]
 *   sortKey : key de colonne actuellement triée (UI only, tri fait côté parent)
 *   sortDir : 'asc' | 'desc'
 *   onSort  : (key) => void
 */
import React from 'react';

export default function SolExpertGrid({ columns = [], rows = [], sortKey, sortDir = 'asc', onSort, className = '' }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        className={`sol-expert-grid ${className}`.trim()}
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 12.5,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        <thead>
          <tr>
            {columns.map((col) => {
              const active = sortKey === col.key;
              return (
                <th
                  key={col.key}
                  onClick={onSort ? () => onSort(col.key) : undefined}
                  style={{
                    textAlign: col.align || 'left',
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: active ? 'var(--sol-ink-900)' : 'var(--sol-ink-500)',
                    fontWeight: 600,
                    borderBottom: '1px solid var(--sol-rule)',
                    padding: '8px 10px',
                    cursor: onSort ? 'pointer' : 'default',
                    WebkitUserSelect: 'none',
                    userSelect: 'none',
                  }}
                >
                  {col.label}
                  {active && <span style={{ marginLeft: 4 }}>{sortDir === 'asc' ? '▲' : '▼'}</span>}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    padding: '9px 10px',
                    borderBottom: '1px solid var(--sol-ink-100)',
                    color: col.num ? 'var(--sol-ink-900)' : 'var(--sol-ink-700)',
                    fontFamily: col.num ? 'var(--sol-font-mono)' : 'var(--sol-font-body)',
                    textAlign: col.align || 'left',
                  }}
                >
                  {row.cells?.[col.key] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p
          style={{
            fontSize: 12.5,
            color: 'var(--sol-ink-400)',
            textAlign: 'center',
            padding: '24px 0',
            margin: 0,
          }}
        >
          Aucune ligne à afficher.
        </p>
      )}
    </div>
  );
}
