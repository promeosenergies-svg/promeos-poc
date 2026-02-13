# PROMEOS UX/UI Spec — Sprint WOW DIAMANT

## Principes

1. **Simple par defaut**: interface epuree, 1 CTA primaire max par ecran
2. **Expert sur demande**: toggle global revelant filtres avances, colonnes, bulk actions
3. **Coherence**: memes patterns partout (PageShell, FilterBar, KpiCard, Toast)
4. **Hierarchie**: titre clair > sous-titre utile > contenu > metadata
5. **Prevention d'erreurs**: validations, empty states, messages actionnables
6. **Performance percue**: skeletons, animations subtiles, lazy loading

## Design Tokens

- **Couleurs semantiques**: primary (blue), success (green), warning (amber), danger (red), neutral (gray)
- **Statuts**: ok/warn/crit/info/neutral (Badge)
- **Risque**: low (green) / medium (amber) / high (orange) / critical (red)
- **Conformite**: conforme (green) / a_risque (orange) / non_conforme (red) / a_evaluer (gray)

## Composants Design System V1

### Existants (13)
Button, Badge, Card/CardHeader/CardBody, Input, Select, Tabs, Table, Pagination, Skeleton, EmptyState, ErrorState, TrustBadge, Modal

### Nouveaux (9)
- **PageShell**: wrapper page standard (title, subtitle, icon, actions, children)
- **KpiCard**: carte KPI unifiee (icon, title, value, sub, badge, color)
- **FilterBar**: barre de filtres horizontale (children, onReset, count)
- **Toggle**: switch Simple/Expert (checked, onChange, label)
- **Tooltip**: infobulle CSS-only (text, children, position)
- **Progress**: barre de progression (value, color, label)
- **Toast + ToastProvider**: notifications ephemeres (useToast hook)
- **Drawer**: panel coulissant (open, onClose, title, side)

## Navigation

- **Sidebar**: 5 sections, collapsible, badges, permission filtering
- **Command Palette**: Ctrl+K, recherche pages + actions rapides
- **Breadcrumb**: pathname labels FR
- **ScopeSwitcher**: Org > Portefeuille > Site

## Expert Mode

- Toggle dans TopBar (entre recherche et UserMenu)
- Persiste dans localStorage (cle: `promeos_expert`)
- Pattern: `{isExpert && <AdvancedContent />}`
- Pages non-compatibles: inaffectees

## Checklist par page

- [ ] PageShell avec titre + sous-titre + icon + actions
- [ ] KpiCard pour metriques principales
- [ ] FilterBar standard pour filtres
- [ ] EmptyState quand pas de donnees
- [ ] Skeleton pour chargement
- [ ] Toast pour feedback async
- [ ] Expert Mode gates si applicable
- [ ] track() pour analytics
- [ ] useScope() pour contexte site
- [ ] api.js pour appels API
