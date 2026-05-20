import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, FileUp, MoreHorizontal, Slash, UserPlus } from 'lucide-react';

import { DRAWER_ACTIONS_COPY } from '../constants';
import { isTerminalState } from '../utils/lifecycleTransitions';
import { BlockerAddModal } from './BlockerAddModal';
import { EvidenceUploadModal } from './EvidenceUploadModal';
import { LifecycleTransitionModal } from './LifecycleTransitionModal';

/**
 * M2-5.10.B — Drawer header actions (maquette §8.4 lignes 689-732).
 *
 * 3 boutons cardinal : Transitionner (primary, sombre ink-900) · Réassigner
 * (secondary disabled, dette M3+ owner endpoint manquant) · Plus ▾ (menu
 * dropdown vers les modals existantes Bloquer / Ajouter preuve / Clôturer).
 *
 * `isTerminal` désactive l'ensemble du panneau (item clos → aucune mutation).
 * Le menu Plus ▾ se ferme au clic outside et à la touche Escape.
 */

function MenuItem({ icon: Icon, label, onClick, disabled = false, reason }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={
        'flex w-full items-center gap-2 rounded-[4px] px-2.5 py-1.5 text-left font-sans text-[12.5px] font-medium ' +
        (disabled ? 'cursor-not-allowed' : 'cursor-pointer hover:bg-[color:var(--sol-bg-panel)]')
      }
      style={{
        color: disabled ? 'var(--sol-ink-400)' : 'var(--sol-ink-900)',
      }}
    >
      {Icon && (
        <Icon
          size={12}
          aria-hidden="true"
          style={{ color: disabled ? 'var(--sol-ink-400)' : 'var(--sol-ink-500)' }}
        />
      )}
      <span className="flex-1">{label}</span>
      {reason && (
        <span className="font-mono text-[9px] italic" style={{ color: 'var(--sol-ink-400)' }}>
          {reason}
        </span>
      )}
    </button>
  );
}

export function DrawerActions({ item, onTransitionSuccess, onMutated }) {
  const [transitionOpen, setTransitionOpen] = useState(false);
  const [blockerOpen, setBlockerOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const isTerminal = isTerminalState(item?.lifecycle_state);
  const transitionDisabledHint = isTerminal
    ? 'État terminal — aucune transition possible'
    : undefined;

  // Ferme le menu au clic outside + Escape (a11y MV3).
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const handleMenuItem = useCallback((open) => {
    setMenuOpen(false);
    open();
  }, []);

  if (!item) return null;

  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-1.5"
      role="toolbar"
      aria-label="Actions de l'item"
    >
      {/* Primary — Transitionner (sombre ink-900). */}
      <button
        type="button"
        onClick={() => setTransitionOpen(true)}
        disabled={isTerminal}
        title={transitionDisabledHint}
        className="inline-flex items-center gap-1.5 rounded-[6px] border px-3.5 py-2 font-sans text-[12.5px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
        style={{
          background: 'var(--sol-ink-900)',
          color: 'var(--sol-bg-paper)',
          borderColor: 'var(--sol-ink-900)',
        }}
      >
        <Check size={12} aria-hidden="true" />
        {DRAWER_ACTIONS_COPY.primaryLabel}
        <span
          className="ml-1 border-l pl-2 font-mono text-[9px] uppercase tracking-[0.08em]"
          style={{
            borderColor: 'rgba(255,255,255,0.18)',
            color: 'var(--sol-ink-300)',
          }}
        >
          {DRAWER_ACTIONS_COPY.primaryHint}
        </span>
      </button>

      {/* Secondary — Réassigner (dette M3+ endpoint owner). */}
      <button
        type="button"
        disabled
        title={DRAWER_ACTIONS_COPY.secondaryDisabledHint}
        className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-[6px] border px-3 py-2 font-sans text-[12px] font-medium opacity-60"
        style={{
          background: 'var(--sol-bg-paper)',
          color: 'var(--sol-ink-900)',
          borderColor: 'var(--sol-ink-300)',
        }}
      >
        <UserPlus size={11} aria-hidden="true" style={{ color: 'var(--sol-ink-500)' }} />
        {DRAWER_ACTIONS_COPY.secondaryLabel}
      </button>

      {/* More — Plus ▾ avec menu dropdown. */}
      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          aria-label={DRAWER_ACTIONS_COPY.moreAriaLabel}
          className="inline-flex items-center gap-1.5 rounded-[6px] border px-3 py-2 font-sans text-[12px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
          style={{
            background: 'var(--sol-bg-paper)',
            color: 'var(--sol-ink-900)',
            borderColor: 'var(--sol-ink-300)',
          }}
        >
          <MoreHorizontal size={11} aria-hidden="true" style={{ color: 'var(--sol-ink-500)' }} />
          {DRAWER_ACTIONS_COPY.moreLabel}
          <ChevronDown size={11} aria-hidden="true" style={{ color: 'var(--sol-ink-500)' }} />
        </button>

        {menuOpen && (
          <div
            role="menu"
            className="absolute right-0 z-10 mt-1.5 w-[240px] rounded-[6px] border p-1 shadow-lg"
            style={{
              background: 'var(--sol-bg-paper)',
              borderColor: 'var(--sol-rule)',
              boxShadow: '0 8px 24px rgba(15, 23, 42, 0.12)',
            }}
          >
            <MenuItem
              icon={Slash}
              label={DRAWER_ACTIONS_COPY.menuItemBlock}
              disabled={isTerminal}
              onClick={() => handleMenuItem(() => setBlockerOpen(true))}
            />
            <MenuItem
              icon={FileUp}
              label={DRAWER_ACTIONS_COPY.menuItemEvidence}
              disabled={isTerminal}
              onClick={() => handleMenuItem(() => setEvidenceOpen(true))}
            />
            <MenuItem
              icon={Check}
              label={DRAWER_ACTIONS_COPY.menuItemClose}
              disabled={isTerminal}
              onClick={() => handleMenuItem(() => setTransitionOpen(true))}
            />
            <div
              className="my-1 h-px"
              style={{ background: 'var(--sol-rule)' }}
              aria-hidden="true"
            />
            {/* Fusionner — toujours désactivé MV3 (pas d'engine doublons). */}
            <MenuItem
              icon={MoreHorizontal}
              label={DRAWER_ACTIONS_COPY.menuItemMerge}
              disabled
              reason={DRAWER_ACTIONS_COPY.menuItemMergeReason}
            />
          </div>
        )}
      </div>

      {transitionOpen && (
        <LifecycleTransitionModal
          open
          onClose={() => setTransitionOpen(false)}
          itemId={item.id}
          currentState={item.lifecycle_state}
          onSuccess={onTransitionSuccess}
        />
      )}

      {blockerOpen && (
        <BlockerAddModal
          open
          onClose={() => setBlockerOpen(false)}
          itemId={item.id}
          onSuccess={onMutated}
        />
      )}

      {evidenceOpen && (
        <EvidenceUploadModal
          open
          onClose={() => setEvidenceOpen(false)}
          itemId={item.id}
          onSuccess={onMutated}
        />
      )}
    </div>
  );
}
