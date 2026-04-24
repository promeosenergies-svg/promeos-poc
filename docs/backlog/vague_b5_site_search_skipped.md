# Backlog — B5 Site search inline (SKIP Sprint 1 Vague B)

> **Date** : 2026-04-23 · **Phase** : Sprint 1 Vague B B5
> **Décision** : SKIP documenté, reprise Sprint 2 si besoin

## Justification SKIP

### Couverture actuelle
- `ScopeSwitcher` dans le header SolAppShell (desktop) +
  footer SolPanel (mobile via drawer) → recherche de sites par scope
- `CommandPalette` `Ctrl+K` → recherche floue cross-navigation +
  pages + actions

Ensemble couvre ~80% des cas d'usage "trouver/changer de site". B5
serait un 3ᵉ canal redondant.

### Coût / valeur
- Effort : ~1h (composant debounced 300ms + dropdown highlight +
  keyboard nav arrows + mock API fetch sites)
- LOC attendu : ~150 lignes (non-trivial pour une duplication UX)
- Valeur différentielle vs ScopeSwitcher+CommandPalette : **faible**

### Budget Vague B
- Phases A-B4 + bonus refacto : ~2h30 consommées
- Post-Vague : audit 3× parallèle + /simplify + bilan ~45 min
- Marge restante : suffit B5 mais réduit la rigueur post-audit

Priorité rigueur audit > feature redondante.

## Reprise conditionnelle Sprint 2

**Déclencheurs du user-test Sprint 1** (24-72h) qui justifieraient B5 :
1. Feedback qualitatif "je ne trouve pas rapidement un site" sur
   mobile où ScopeSwitcher est moins visible (dans drawer).
2. Tracker analytics : ratio `scope_change` / `nav_panel_opened`
   anormalement bas → utilisateurs ne trouvent pas le ScopeSwitcher.

Si déclencheurs → Sprint 2 Vague C ou D peut inclure B5 avec spec :
- Composant `SolSiteSearch` dans SolPanel (section dédiée entre
  Récents et NAV)
- Debounce 300ms sur `getSites({ q: query })`
- Dropdown keyboard nav (ArrowUp/Down/Enter/Escape)
- Highlight matching substring
- `~150 L` + 10+ tests

## Critères Done si reprise

- [ ] Ne duplique pas ScopeSwitcher (différencie search sites vs
  change scope)
- [ ] WCAG 2.1 AA : dropdown `role=listbox`, items `role=option`,
  `aria-selected`, `aria-activedescendant`
- [ ] Keyboard ArrowDown/Up/Enter/Escape complet
- [ ] Hit area >= 44×44 pour items dropdown
- [ ] Tracker `site_search_applied` avec source manual/deep_link
