/**
 * PROMEOS — SolPanel (240px)
 * Titre module + description + sections avec items (depuis NavRegistry).
 * Lit le registry, la route courante. Zéro fetch.
 *
 * Props :
 *   desc       : override description (sinon lit NAV_MODULES.desc)
 *   badges     : { [route]: string } — compteurs contextuels (ex. notifications)
 *   isExpert   : filtre items expertOnly
 *   rightSlot  : optionnel (ex. bouton "Réduire panel")
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Lock, Star } from 'lucide-react';
import {
  resolveModule,
  getPanelSections,
  NAV_MODULES,
  ROUTE_MODULE_MAP,
} from '../../layout/NavRegistry';
import { resolveBackendPermissionKey } from '../../layout/permissionMap';
import { useAuth } from '../../contexts/AuthContext';
import { track } from '../../services/tracker';
import { getPins, togglePin, isPinned } from '../../utils/navPins';
import { FOCUS_RING_SOL } from './focusRing';

const LOCKED_TOOLTIP = 'Module non inclus dans votre rôle. Contactez votre administrateur.';

// Clé de section utilisée par getPanelSections (NavRegistry) pour
// distinguer un click sur un raccourci paramétré d'un item top-level.
const DEEP_LINK_SECTION_KEY = 'deep-links';

// Précédence : locked > active > default. Évite la ternary chain inline.
function getItemVisuals(locked, isActive) {
  if (locked) {
    return {
      color: 'var(--sol-ink-500)',
      background: 'transparent',
      fontWeight: 400,
      cursor: 'not-allowed',
    };
  }
  if (isActive) {
    return {
      color: 'var(--sol-calme-fg)',
      background: 'var(--sol-calme-bg)',
      fontWeight: 500,
      cursor: 'pointer',
    };
  }
  return {
    color: 'var(--sol-ink-700)',
    background: 'transparent',
    fontWeight: 400,
    cursor: 'pointer',
  };
}

// Table key → index transformer. Évite la cascade if/else pour
// ArrowDown/Up/Home/End.
const KEY_NAV_NEXT = {
  ArrowDown: (idx, len) => (idx === -1 ? 0 : Math.min(idx + 1, len - 1)),
  ArrowUp: (idx, len) => (idx === -1 ? len - 1 : Math.max(idx - 1, 0)),
  Home: () => 0,
  End: (_idx, len) => len - 1,
};

// Bouton Pin/Unpin — toujours rendu mais opacity contrôlée :
// visible à 100% si pinné, au hover/focus sinon. Pas de render conditionnel
// pour éviter le reflow quand on toggle un item sur/de la liste.
function PanelPinButton({ itemKey, itemLabel, pinned, onToggle }) {
  return (
    <button
      type="button"
      onClick={(e) => onToggle(itemKey, e)}
      aria-label={pinned ? `Désépingler ${itemLabel}` : `Épingler ${itemLabel}`}
      aria-pressed={pinned}
      data-testid={`sol-panel-pin-${itemKey}`}
      className={`sol-panel-pin ${FOCUS_RING_SOL}`.trim()}
      style={{
        background: 'transparent',
        border: 'none',
        padding: 2,
        cursor: 'pointer',
        color: pinned ? 'var(--sol-attention-fg)' : 'var(--sol-ink-400)',
        opacity: pinned ? 1 : 0,
        transition: 'opacity 120ms ease, color 120ms ease',
        flexShrink: 0,
      }}
    >
      <Star size={12} fill={pinned ? 'currentColor' : 'none'} aria-hidden="true" />
    </button>
  );
}

export default function SolPanel({
  desc,
  badges = {},
  isExpert = false,
  rightSlot = null,
  headerSlot = null,
  footerSlot = null,
  className = '',
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, hasPermission } = useAuth();
  const currentModule = resolveModule(location.pathname);
  const moduleMeta = NAV_MODULES.find((m) => m.key === currentModule);
  // V2 : panelSections par route (maquette) avec fallback sur NAV_SECTIONS
  const rawSections = getPanelSections(location.pathname, isExpert);

  // Pins (B1) : localStorage ne déclenche pas React, on force re-render via
  // un counter incrémenté après chaque toggle.
  const [pinsVersion, setPinsVersion] = React.useState(0);
  const pins = React.useMemo(
    () => getPins(),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pinsVersion]
  );
  const handleTogglePin = React.useCallback((itemKey, event) => {
    event.preventDefault();
    event.stopPropagation();
    togglePin(itemKey);
    setPinsVersion((v) => v + 1);
  }, []);

  // Tracker A10 : event `nav_panel_opened` au mount + au changement de module.
  // Permet de mesurer la fenêtre Test milieu (ratio clicks deep-link / panels
  // ouverts) et la valeur du système de raccourcis en conditions réelles.
  React.useEffect(() => {
    track('nav_panel_opened', {
      module: currentModule,
      route: location.pathname,
      is_expert: isExpert,
    });
  }, [currentModule, location.pathname, isExpert]);

  // Handler click items : wrap navigate() avec tracker.
  // Différencie deep-link (section 'deep-links') d'un item NAV_SECTIONS
  // top-level — crucial pour la mesure Sprint 1→2.
  const handleItemClick = React.useCallback(
    (item, sectionKey) => {
      const isDeepLink = sectionKey === DEEP_LINK_SECTION_KEY;
      track('nav_deep_link_click', {
        href: item.to,
        label: item.label,
        module: currentModule,
        section_key: sectionKey,
        is_deep_link: isDeepLink,
      });
      navigate(item.to);
    },
    [navigate, currentModule]
  );

  // Permissions : items visibles avec `locked: boolean` plutôt que masqués
  // (cadenas + tooltip = transparence + upsell). Pas de filter pré-auth.
  // Clavier : Escape blur l'item actif, ArrowDown/Up/Home/End naviguent
  // entre items de sections différentes (flat tab-order). Les items
  // lockés restent focusables pour que le cadenas soit découvrable
  // au clavier.
  const handlePanelKeyDown = React.useCallback((e) => {
    if (e.key === 'Escape') {
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
      return;
    }
    const nextFn = KEY_NAV_NEXT[e.key];
    if (!nextFn) return;
    const buttons = Array.from(e.currentTarget.querySelectorAll('button.sol-panel-item'));
    if (buttons.length === 0) return;
    const idx = buttons.indexOf(document.activeElement);
    const next = nextFn(idx, buttons.length);
    e.preventDefault();
    buttons[next]?.focus();
    buttons[next]?.scrollIntoView({ block: 'nearest' });
  }, []);

  const sections = React.useMemo(() => {
    if (!isAuthenticated) {
      return rawSections.map((section) => ({
        ...section,
        items: (section.items || []).map((item) => ({ ...item, locked: false })),
      }));
    }
    return rawSections
      .map((section) => ({
        ...section,
        items: (section.items || []).map((item) => {
          if (item.requireAdmin) {
            return { ...item, locked: !hasPermission('admin') };
          }
          const basePath = item.to.split('?')[0].split('#')[0];
          const navModule = ROUTE_MODULE_MAP[basePath];
          if (navModule === undefined) return { ...item, locked: false };
          const backendKey = resolveBackendPermissionKey(navModule);
          const allowed = hasPermission('view', backendKey) || hasPermission('admin');
          return { ...item, locked: !allowed };
        }),
      }))
      .filter((section) => section.items.length > 0);
  }, [rawSections, isAuthenticated, hasPermission]);

  // Items épinglés résolus contre les sections courantes (cross-modules OK,
  // on pioche dans tout ce qui est actuellement visible). Un pin qui pointe
  // vers un item masqué (permissions/expert mode) disparaît silencieusement.
  const pinnedItems = React.useMemo(() => {
    const allItems = sections.flatMap((s) => s.items || []);
    return pins.map((key) => allItems.find((it) => it.to === key)).filter(Boolean);
  }, [pins, sections]);

  return (
    <aside
      className={`sol-panel sol-app-panel ${className}`.trim()}
      aria-label="Navigation contextuelle"
      onKeyDown={handlePanelKeyDown}
      style={{
        background: 'var(--sol-bg-paper)',
        borderRight: '1px solid var(--sol-rule)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0, // critical pour laisser l'enfant scroll dans un flex parent
      }}
    >
      {/* Header slot — reste visible (pas sticky — naturellement au-dessus
          du flex:1 scroll area, donc toujours accessible). */}
      {headerSlot}
      {/* Scroll zone : sections navigation, flex:1 + overflowY auto */}
      <div
        className="sol-panel-body"
        style={{
          padding: '16px 14px 0',
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
        }}
      >
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginBottom: 4,
          }}
        >
          <h2
            className="sol-panel-module"
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 18,
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
              letterSpacing: '-0.015em',
              margin: 0,
            }}
          >
            {moduleMeta?.label || 'Navigation'}
          </h2>
          {rightSlot}
        </header>
        <p
          className="sol-panel-desc"
          style={{
            fontSize: 12.5,
            color: 'var(--sol-ink-500)',
            lineHeight: 1.45,
            margin: '0 0 18px 0',
          }}
        >
          {desc || moduleMeta?.desc || ''}
        </p>

        {/* Section Épinglés (B1) — affichée uniquement quand pins non-vide */}
        {pinnedItems.length > 0 && (
          <div
            key="pinned"
            className="sol-panel-section"
            style={{ marginBottom: 20 }}
            aria-label="Items épinglés"
          >
            <p
              className="sol-panel-section-label"
              style={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 9.5,
                textTransform: 'uppercase',
                letterSpacing: '0.14em',
                fontWeight: 600,
                color: 'var(--sol-ink-400)',
                margin: '0 0 8px 2px',
              }}
            >
              Épinglés
            </p>
            {pinnedItems.map((item) => {
              const basePath = item.to.split('?')[0].split('#')[0];
              const isActive =
                basePath === location.pathname ||
                (basePath !== '/' && location.pathname.startsWith(basePath + '/'));
              const locked = item.locked === true;
              const visuals = getItemVisuals(locked, isActive);
              return (
                <div
                  key={`pinned-${item.to}`}
                  className="sol-panel-item-row"
                  style={{
                    display: 'flex',
                    alignItems: 'stretch',
                    position: 'relative',
                  }}
                >
                  <button
                    type="button"
                    onClick={locked ? undefined : () => handleItemClick(item, 'pinned')}
                    aria-current={isActive && !locked ? 'page' : undefined}
                    aria-disabled={locked || undefined}
                    title={locked ? LOCKED_TOOLTIP : undefined}
                    data-locked={locked || undefined}
                    className={`sol-panel-item ${FOCUS_RING_SOL} ${isActive ? 'is-active' : ''}${locked ? ' is-locked' : ''}`.trim()}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '7px 8px',
                      paddingRight: 32, // place pour le PanelPinButton absolute
                      borderRadius: 4,
                      fontSize: 13,
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      transition: 'background 120ms ease',
                      ...visuals,
                    }}
                  >
                    <span style={{ flex: 1, lineHeight: 1.3 }}>{item.label}</span>
                  </button>
                  <div
                    style={{
                      position: 'absolute',
                      right: 6,
                      top: '50%',
                      transform: 'translateY(-50%)',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    <PanelPinButton
                      itemKey={item.to}
                      itemLabel={item.label}
                      pinned
                      onToggle={handleTogglePin}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {sections.map((section) => {
          const items = section.items || [];
          if (items.length === 0) return null;
          return (
            <div key={section.key} className="sol-panel-section" style={{ marginBottom: 20 }}>
              <p
                className="sol-panel-section-label"
                style={{
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 9.5,
                  textTransform: 'uppercase',
                  letterSpacing: '0.14em',
                  fontWeight: 600,
                  color: 'var(--sol-ink-400)',
                  margin: '0 0 8px 2px',
                }}
              >
                {section.label}
              </p>
              {items.map((item) => {
                const basePath = item.to.split('?')[0].split('#')[0];
                const isActive =
                  basePath === location.pathname ||
                  (basePath !== '/' && location.pathname.startsWith(basePath + '/'));
                const badge = badges[basePath] ?? badges[item.to];
                const locked = item.locked === true;
                const visuals = getItemVisuals(locked, isActive);
                const pinned = isPinned(item.to);
                return (
                  <div
                    key={item.to}
                    className="sol-panel-item-row"
                    style={{
                      display: 'flex',
                      alignItems: 'stretch',
                      position: 'relative',
                    }}
                  >
                    <button
                      type="button"
                      onClick={locked ? undefined : () => handleItemClick(item, section.key)}
                      aria-current={isActive && !locked ? 'page' : undefined}
                      aria-disabled={locked || undefined}
                      title={locked ? LOCKED_TOOLTIP : undefined}
                      data-locked={locked || undefined}
                      className={`sol-panel-item ${FOCUS_RING_SOL} ${isActive ? 'is-active' : ''}${locked ? ' is-locked' : ''}`.trim()}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '7px 8px',
                        paddingRight: 32, // place pour le PanelPinButton absolute
                        borderRadius: 4,
                        fontSize: 13,
                        width: '100%',
                        textAlign: 'left',
                        border: 'none',
                        transition: 'background 120ms ease',
                        ...visuals,
                      }}
                    >
                      <span style={{ flex: 1, lineHeight: 1.3 }}>
                        {item.label}
                        {item.desc && (
                          <span
                            className="sol-panel-item-desc"
                            style={{
                              display: 'block',
                              fontSize: 11,
                              color: 'var(--sol-ink-400)',
                              marginTop: 1,
                              lineHeight: 1.35,
                              fontWeight: 400,
                            }}
                          >
                            {item.desc}
                          </span>
                        )}
                      </span>
                      {locked && (
                        <>
                          <Lock
                            size={12}
                            aria-hidden="true"
                            data-testid="sol-panel-item-lock"
                            style={{ color: 'var(--sol-ink-500)', flexShrink: 0 }}
                          />
                          <span className="sr-only">— {LOCKED_TOOLTIP}</span>
                        </>
                      )}
                      {badge != null && (
                        <span
                          className="sol-panel-item-badge"
                          style={{
                            fontFamily: 'var(--sol-font-mono)',
                            fontSize: 10,
                            background: 'var(--sol-afaire-bg)',
                            color: 'var(--sol-afaire-fg)',
                            padding: '1px 5px',
                            borderRadius: 2,
                            fontWeight: 600,
                          }}
                        >
                          {badge}
                        </span>
                      )}
                    </button>
                    {!locked && (
                      <div
                        style={{
                          position: 'absolute',
                          right: 6,
                          top: '50%',
                          transform: 'translateY(-50%)',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        <PanelPinButton
                          itemKey={item.to}
                          itemLabel={item.label}
                          pinned={pinned}
                          onToggle={handleTogglePin}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
      {footerSlot}
    </aside>
  );
}
