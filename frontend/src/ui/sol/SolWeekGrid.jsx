/**
 * PROMEOS — SolWeekGrid
 * Grid 3 colonnes gap 12. Accueille 3 SolWeekCard (À regarder / À faire / Bonne nouvelle).
 */
import React from 'react';

export default function SolWeekGrid({ children, className = '' }) {
  return (
    <div
      className={`sol-week-grid ${className}`.trim()}
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 12,
        margin: '14px 0 24px 0',
      }}
    >
      {children}
    </div>
  );
}
