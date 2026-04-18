/**
 * PROMEOS — SolAppShell
 * Layout grid 56 / 240 / 1fr / 36px (rail / panel / main / timerail).
 * Composition pure : chaque zone est un composant Sol ou un prop.
 *
 * Props :
 *   children         : contenu principal (une page)
 *   railProps        : { role, isExpert }
 *   panelProps       : { desc, badges, isExpert, rightSlot }
 *   timerailProps    : props pour SolTimerail
 *   cartoucheState   : 'default' | 'proposing' | 'pending' | 'executing' | 'done' (null = hide)
 *   onCartoucheClick : callback
 */
import React from 'react';
import SolRail from './SolRail';
import SolPanel from './SolPanel';
import SolTimerail from './SolTimerail';
import SolCartouche from './SolCartouche';

export default function SolAppShell({
  children,
  railProps = {},
  panelProps = {},
  timerailProps,
  cartoucheState = 'default',
  onCartoucheClick,
  className = '',
}) {
  return (
    <div
      className={`sol-app ${className}`.trim()}
      style={{
        display: 'grid',
        gridTemplateColumns: '56px 240px 1fr',
        gridTemplateRows: '1fr 36px',
        gridTemplateAreas: '"rail panel main" "rail panel timerail"',
        minHeight: '100vh',
        background: 'var(--sol-bg-canvas)',
        color: 'var(--sol-ink-900)',
        fontFamily: 'var(--sol-font-body)',
      }}
    >
      <SolRail {...railProps} />
      <SolPanel {...panelProps} />
      <main
        className="sol-app-main"
        style={{
          gridArea: 'main',
          overflowY: 'auto',
          padding: '32px 48px 60px 48px',
        }}
      >
        {children}
      </main>
      <div style={{ gridArea: 'timerail' }}>
        {timerailProps ? <SolTimerail {...timerailProps} /> : null}
      </div>
      {cartoucheState && <SolCartouche state={cartoucheState} onClick={onCartoucheClick} />}
    </div>
  );
}
