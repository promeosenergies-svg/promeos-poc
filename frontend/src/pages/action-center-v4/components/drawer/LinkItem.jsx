import Tooltip from '../../../../ui/Tooltip';

import {
  LINKS_COPY,
  TARGET_MODULE_DISABLED_TOOLTIP,
  TARGET_MODULE_LABELS,
  TARGET_MODULE_UI_AVAILABLE,
} from '../../constants';

/**
 * M2-5.3.B / M2-5.10.B — Link row Sol (maquette §8.4 lignes 549-559).
 *
 * Layout grid 140px label MONO + 1fr value + auto action ↗. `action_center_
 * item` est affiché en valeur ; les 6 autres target_module sont disabled +
 * tooltip. Aucun filtrage silencieux — tous les links sont rendus.
 *
 * Le `target_id` (UUID) est tronqué pour la lisibilité (cohérent doctrine
 * §13.5 anti-bruit visuel).
 */
export function LinkItem({ link }) {
  const moduleLabel = TARGET_MODULE_LABELS[link.target_module] || link.target_module;
  const isAvailable = TARGET_MODULE_UI_AVAILABLE.includes(link.target_module);

  // Tronque le UUID à 8 caractères pour le visible (le hover natif title
  // expose la valeur complète).
  const truncatedId =
    typeof link.target_id === 'string' && link.target_id.length > 12
      ? `${link.target_id.slice(0, 8)}…`
      : link.target_id;

  const content = (
    <article
      className={
        'grid items-center gap-2.5 rounded-[4px] border px-3 py-1.5' +
        (isAvailable ? '' : ' opacity-60')
      }
      style={{
        gridTemplateColumns: '140px 1fr auto',
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      <span
        className="font-mono text-[9.5px] font-medium uppercase tracking-[0.08em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        {moduleLabel}
      </span>
      <span
        className="truncate text-[12.5px] font-medium"
        style={{
          color: isAvailable ? 'var(--sol-ink-900)' : 'var(--sol-ink-400)',
          fontStyle: isAvailable ? 'normal' : 'italic',
        }}
        title={link.target_id}
      >
        {link.relation && (
          <span className="mr-2 font-mono text-[10px]" style={{ color: 'var(--sol-ink-500)' }}>
            {link.relation} ·
          </span>
        )}
        {truncatedId || LINKS_COPY.noneFallback}
      </span>
      {isAvailable && link.link_type ? (
        <a
          href="#"
          onClick={(e) => e.preventDefault()}
          className="font-mono text-[9.5px] font-semibold uppercase tracking-[0.06em] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
          style={{
            color: 'var(--sol-ink-900)',
            borderBottom: '1px solid var(--sol-ink-900)',
            paddingBottom: '1px',
            textDecoration: 'none',
          }}
        >
          {LINKS_COPY.linkActionOpen}
        </a>
      ) : (
        <span />
      )}
    </article>
  );

  if (isAvailable) return content;
  return <Tooltip text={TARGET_MODULE_DISABLED_TOOLTIP}>{content}</Tooltip>;
}
