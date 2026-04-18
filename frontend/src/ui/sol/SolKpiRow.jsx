/**
 * PROMEOS — SolKpiRow
 * Grid 3 colonnes exactes (ou 1 col en mobile <960px). Accueille 3 SolKpiCard.
 */
import React from 'react';

export default function SolKpiRow({ children, className = '', columns = 3 }) {
  return (
    <div
      className={`sol-kpi-row ${className}`.trim()}
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: 14,
        margin: '18px 0 24px 0',
      }}
    >
      {children}
    </div>
  );
}
