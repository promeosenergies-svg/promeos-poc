/**
 * SolPageHeader — header éditorial des pages cockpit/tableau de bord.
 *
 * Pattern « journal en terrasse » de la refonte v1, porté sur sol2 :
 *   - Kicker mono uppercase letter-spaced (« ACCUEIL · GROUPE HELIOS · 5 SITES »)
 *   - Titre Fraunces serif avec italic-hook éditorial (« Tableau de bord — _opérationnel_ »)
 *   - Subtitle DM Sans 13px gris pour contexte
 *   - Right slot pour actions (DataFreshnessBadge, BoutonRapport, etc.)
 *
 * Audit UI Phase 2 : signature visuelle Sol était sous-exploitée (titres plats,
 * pas de kicker, pas d'italic-hook). Ce composant matérialise l'identité
 * éditoriale Fraunces déjà chargée mais non visible.
 *
 * Display-only — aucun calcul métier.
 */

/**
 * Prop `italicHook` (renommée depuis `hook` /simplify Phase 3 — éviter
 * la collision sémantique avec les React hooks à la lecture).
 */
export default function SolPageHeader({
  kicker,
  title,
  italicHook,
  subtitle,
  rightSlot,
  className = '',
}) {
  return (
    <header
      className={`flex items-end justify-between gap-4 flex-wrap pb-3 mb-2 ${className}`}
      data-testid="sol-page-header"
    >
      <div className="min-w-0 flex-1">
        {kicker && <p className="sol-page-kicker">{kicker}</p>}
        <h1 className="sol-page-title">
          {title}
          {italicHook && (
            <>
              {' '}
              — <em>{italicHook}</em>
            </>
          )}
        </h1>
        {subtitle && <p className="sol-page-subtitle">{subtitle}</p>}
      </div>
      {rightSlot && <div className="flex items-center gap-3 flex-shrink-0">{rightSlot}</div>}
    </header>
  );
}
