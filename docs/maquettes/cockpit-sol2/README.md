# Maquettes finales Cockpit dual sol2 — guide d'injection Claude Code

> **Statut** : maquettes cibles validées Amine 2026-04-28 · état attendu fin de Phase 2 du sprint refonte.
>
> **Usage** : injecter ces 2 fichiers HTML dans Claude Code aux côtés du `PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md` pour que Claude Code dispose d'une référence visuelle pixel-perfect à chaque phase.

## Fichiers du dossier

| Fichier | Rôle |
|---|---|
| `cockpit-pilotage-briefing-jour.html` | Maquette page Pilotage (Briefing du jour) — energy manager 30 s |
| `cockpit-synthese-strategique.html` | Maquette page Décision (Synthèse stratégique) — dirigeant 3 min |
| `README.md` | Ce fichier — guide d'injection et mapping composants/phases |

## Comment injecter dans Claude Code

### Étape 1 — Copier les maquettes dans le repo

```bash
cd promeos-energies
mkdir -p docs/maquettes/cockpit-sol2
cp /chemin/vers/maquettes/*.html docs/maquettes/cockpit-sol2/
cp /chemin/vers/maquettes/README.md docs/maquettes/cockpit-sol2/
git add docs/maquettes/cockpit-sol2/
git commit -m "docs(maquettes): cockpit dual sol2 — cibles Phase 2 validées Amine 2026-04-28"
```

### Étape 2 — Référencer dans le prompt d'exécution

Le prompt `PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md` mentionne déjà les maquettes en section 7 (Definition of Done globale). Au début de chaque session Claude Code, lui demander explicitement :

> Avant de coder, ouvre `docs/maquettes/cockpit-sol2/cockpit-pilotage-briefing-jour.html` et `docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html`. Ces 2 fichiers sont la cible visuelle de fin de Phase 2. Tout composant que tu créeras doit converger vers cette cible.

### Étape 3 — Vérification visuelle à chaque fin de phase

À chaque fin de phase (0, 1, 2, 3) :
- Capture Playwright des 2 vues en production
- Comparaison côte-à-côte avec les maquettes HTML de référence
- Diff visuel documenté dans `docs/sprints/SPRINT_COCKPIT_DUAL_SOL2.md`

## Mapping composants attendus

### Page Pilotage (`cockpit-pilotage-briefing-jour.html`)

| Composant front à créer | Section maquette | Phase | Endpoint backend |
|---|---|---|---|
| `<SolKickerWithSwitch>` | Header en haut · scope + switch jour/stratégique | Phase 3.1 | `/api/cockpit/_facts.scope` |
| `<SolBriefingHead>` | H1 "Bonjour — voici ce qui mérite votre attention" + narrative | Phase 1.3 | `/api/cockpit/_facts` |
| `<CockpitHeaderPills>` | Bandeau alertes + bouton Centre d'action | Phase 1.3 | `/api/cockpit/_facts.alerts` + `/api/action-center/actions/summary` |
| `<SolKpiTriptyqueEnergetique>` | 3 KPI (Conso J-1 · Surconso 7 j · Pic puissance) | Phase 2.1 | `/api/cockpit/_facts.consumption + .power` |
| `<SolConsoSevenDaysBars>` | SVG barres 7 jours avec annotation samedi | Phase 1.3 | `/api/ems/timeseries?period=7d` |
| `<SolCourbeChargeJMinus1>` | SVG courbe HP/HC + ligne souscrite | Phase 1.3 | `/api/cockpit/cdc?period=j_minus_1` |
| `<SolFileTraitement>` | Liste 5 lignes priorisées par impact énergétique | Phase 0.2 (réécriture) + Phase 2.3 | `/api/cockpit/priorities` |
| `<SolFooter>` | Source · confiance · MAJ · méthodologie | partout | `/api/cockpit/_facts.metadata` |

### Page Synthèse stratégique (`cockpit-synthese-strategique.html`)

| Composant front à créer | Section maquette | Phase | Endpoint backend |
|---|---|---|---|
| `<SolKickerWithSwitch>` | Réutilisé du Pilotage | Phase 3.1 | `/api/cockpit/_facts.scope` |
| `<SolBriefingHead>` exécutif | H1 "Synthèse stratégique" + narrative dense | Phase 1.3 | `/api/cockpit/_facts` |
| `<SolKpiTriptyqueHybride>` | 3 KPI hybride (Trajectoire score · Exposition€ · Potentiel MWh) avec badges Calculé/Modélisé | Phase 2.1 + 2.2 | `/api/cockpit/_facts.compliance + .exposure + .potential_recoverable` |
| `<SolDecisionsTopThree>` | 3 décisions narrées avec drill-downs preuve op | Phase 2.3 + 3.2 | `/api/cockpit/decisions/top3` |
| `<SolTrajectoryDT>` | SVG trajectoire 2030 lissée par échéance | Phase 1.6 | `/api/cockpit/trajectory` |
| `<SolFacturePortefeuille>` | Facture prévisionnelle 5 sites avec composantes inactives collapsées | Phase 1.7 + 0.5 | `/api/purchase/cost-simulation/portfolio/{org_id}` |
| `<SolFlexTeaser>` | 1 card minimaliste vers Flex Intelligence | Phase 0.3 | `/api/cockpit/_facts.flex_potential` |
| `<SolFooter>` | Réutilisé | partout | `/api/cockpit/_facts.metadata` |

## Tokens visuels Sol — référence

Les 2 maquettes utilisent les mêmes tokens CSS que le design system Sol existant. Le bloc `:root {}` en haut de chaque fichier est une copie volontairement dupliquée pour que les maquettes soient autonomes (ouvrables dans n'importe quel navigateur sans dépendance).

**En production**, ces tokens viennent de :
- `frontend/src/ui/sol/tokens.css` (light mode + animations + reduced-motion)
- Convention typo Sol : **Fraunces** display · **DM Sans** body · **JetBrains Mono** numeric (cf `--sol-font-display`/`-body`/`-mono`)
- Vague H Phase 0bis (28/04/2026) : maquettes alignées sur ces 3 fontes
  (Inter/IBM Plex Mono retirés — anti-pattern §6.1 mélange typo hors triptyque)

Si Claude Code détecte des écarts entre tokens des maquettes et tokens en production : **les tokens en production font foi**, les maquettes sont indicatives sur les valeurs.

## Règles de divergence acceptable

Pendant la refonte, les écarts suivants entre maquettes et production sont **acceptables** :

1. **Données dynamiques** : les maquettes contiennent des données HELIOS hardcodées en démo. La production charge les vraies données via API.
2. **États interactifs** : hover, focus, loading skeletons ne sont pas matérialisés dans les maquettes. La production doit les implémenter selon design system Sol.
3. **Mode sombre** : les maquettes sont en light mode uniquement. La production doit supporter dark mode automatique via CSS variables.
4. **Responsive** : les maquettes sont conçues pour desktop 1280 px+. La production doit supporter tablette (768-1024) et mobile (375-767), avec adaptation des grilles.
5. **Animations Sol** : transitions, easing, micro-interactions ne sont pas dans les maquettes. La production hérite des règles du design system.

## Règles de divergence NON acceptable

Les écarts suivants sont **bloquants** et déclenchent un retour en arrière :

1. **Structure d'information** : ordre des sections, hiérarchie visuelle, position relative des blocs doit être identique entre maquette et production.
2. **Triptyque KPI hero** : exactement 3 KPI, jamais 2 ni 4, dans l'ordre exact de la maquette.
3. **Badges de confiance** : `Calculé` (vert) ou `Modélisé` (ambre) sous chaque chiffre €. Jamais d'autre valeur, jamais omis.
4. **Acronymes en récit** : aucun acronyme brut (DT/BACS/GTB/TURPE/APER/OPERAT/CDC/VNU/CBAM/ARENH) dans les titres ou cards. La production utilise le dictionnaire `acronym_to_narrative.py` (Phase 1.8).
5. **Switch éditorial intégré au kicker** : pas de tabs séparées, pas de doublon nav. Un seul switch dans le kicker mono.
6. **Drill-downs systématiques** : chaque KPI hero a un lien drill-down. Chaque décision a un lien preuve opérationnelle.
7. **Footer source · confiance · MAJ** : présent sur toutes les vues, avec lien méthodologie.

## Checklist de validation pixel-perfect

Avant de considérer une phase comme terminée, comparer maquette vs production sur :

- [ ] Hiérarchie typo (Fraunces serif sur H1 narrative + KPI values, Inter sur body, IBM Plex Mono sur kickers/footers)
- [ ] Espacement vertical (rythme rem cohérent : 1rem entre sections, 1.5rem avant blocs majeurs)
- [ ] Bordures (toujours 0.5px, jamais 1px sauf accent featured 2px)
- [ ] Border-radius (md=8px partout, lg=12px sur cards majeures)
- [ ] Backgrounds (jamais hardcoded, toujours via CSS variables `--color-background-*`)
- [ ] Text colors (jamais black absolu, toujours via CSS variables `--color-text-*`)
- [ ] Largeur max 1280 px pour desktop
- [ ] Respect du triptyque (3 KPI hero sur grid `repeat(3, minmax(0, 1fr))`)
- [ ] Tooltips fonctionnels sur les `?` à côté des labels KPI
- [ ] Liens internes fonctionnels (anchors `#decision-bacs-siege`, `#row-bacs-siege`)

## Changelog des maquettes

| Date | Changement | Trigger |
|---|---|---|
| 2026-04-28 | v1.0 — maquettes finales validées Amine | Décisions arbitrages 1-10 + EUR/MWh + baseline |

Ces maquettes seront mises à jour à la fin de chaque sprint si nécessaire (ex: Phase 4 test utilisateur révèle un point bloquant). Toute mise à jour fait l'objet d'un commit séparé avec changelog ici.

## Anti-patterns visuels à NE PAS introduire pendant la refonte

(Doctrine §6.3 + arbitrages Amine sprint Cockpit dual)

- ❌ Card "Bienvenue PROMEOS" en pleine largeur sans densité d'info
- ❌ Card "Gain simulé empty" anti-pattern empty state
- ❌ 4 KPI hero (le triptyque est inviolable)
- ❌ Acronymes bruts en titres (`DT`, `BACS`, `GTB`, etc.)
- ❌ Chiffre € sans badge de confiance et sans tooltip avec source
- ❌ KPI Leviers en € heuristique (`8500 €/site` interdit)
- ❌ Dashboard avec ≥10 cards (dérive widget-empilement)
- ❌ Doublon navigation tabs + sidebar
- ❌ Card Hypermarché Montreuil en scope HELIOS (leak slug `retail-001`)
- ❌ Bandeau Pilotage usages avec 4 sub-cards en Vue Exécutive (déplacé sur page Flex Intelligence dédiée)

## Doctrine compliance checklist

Les 2 maquettes respectent les 8 DoD doctrinales §11.3 :

- [x] DoD 1 : Synthèse stratégique lisible 3 min (narrative 4 lignes + 3 KPI + 3 décisions + trajectoire + facture + flex teaser = ~8 blocs)
- [x] DoD 2 : Briefing du jour utile 30 s (3 KPI + 2 visuels + 5 lignes file = 5 blocs)
- [x] DoD 3 : Source unique (mêmes 11 alertes / 4 229 MWh / 37/100)
- [x] DoD 4 : Risque exécutif → preuve op (drill-down `voir preuve opérationnelle →` sur chaque décision)
- [x] DoD 5 : Alerte op → risque exé (lien `voir impact stratégique →` sur P1, P2, P5)
- [x] DoD 6 : Centre d'action relie (bouton header Pilotage + référencé dans décisions)
- [x] DoD 7 : Pas un empilement de widgets (ratio ≤ 7 blocs visibles à l'ouverture)
- [x] DoD 8 : Promesse PROMEOS quoi/pourquoi/combien/action systématique sur chaque ligne

---

**Maquettes cibles Cockpit dual sol2 — guide d'injection Claude Code · v1.0 · 2026-04-28**
