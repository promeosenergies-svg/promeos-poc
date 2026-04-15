# REFONTE COCKPIT V3 — Plan de restructuration UX
**Date** : 2026-03-16
**Branche** : `ux/cockpit-v3`
**Statut** : Plan + mapping — implémentation en cours

---

## 1. DIAGNOSTIC — STRUCTURE ACTUELLE (16 sections)

| # | Section | Composant | Rôle | Verdict |
|---|---------|-----------|------|---------|
| 1 | Error banner | `ErrorState` | Erreur chargement | OK — garder |
| 2 | Résumé exécutif | `ExecutiveSummaryCard` | 3 bullets (positif/négatif/opportunité) | FUSIONNER avec #4 |
| 3 | Health Summary | `HealthSummary` | Bandeau vert/orange/rouge | FUSIONNER avec #2+#4 |
| 4 | Briefing du jour | `BriefingHeroCard` | Actions prioritaires | FUSIONNER → "Priorité" |
| 5 | 4 KPI tiles | `ExecutiveKpiRow` | Conformité, Risque, Maturité, Complétude | GARDER — zone 2 |
| 6 | Impact & Décision | `ImpactDecisionPanel` | Risque conformité + surcoût + optimisation | GARDER — zone 2 (Expert) |
| 7 | Prochaine échéance | inline | Deadline réglementaire + exposition | GARDER — intégrer dans zone 1 |
| 8 | Watchlist | `WatchlistCard` | À surveiller (NC, à risque, sans data) | REPLIER — zone 3 |
| 9 | Market context | `MarketContextCompact` | Prix marché spot | REPLIER — zone 3 Expert |
| 10 | Opportunités | `OpportunitiesCard` | Expert only | REPLIER — zone 3 Expert |
| 11 | Top Sites | `TopSitesCard` | Meilleurs/pires sites | REPLIER — zone 3 |
| 12 | Module Launchers | `ModuleLaunchers` | Tuiles Patrimoine/Énergie/etc. | REPLIER — zone 4 |
| 13 | Consistency banner | `ConsistencyBanner` | Expert warning | REPLIER — zone 3 Expert |
| 14 | Data Quality | `DataQualityWidget` | Expert data quality | REPLIER — zone 4 Expert |
| 15 | Data Activation | `DataActivationPanel` | Briques activées | REPLIER — zone 4 |
| 16 | Essentials Row | `EssentialsRow` | KPI secondaires | REPLIER — zone 4 |
| 17 | Risque résiduel | inline | NC + à risque + CTA action | FUSIONNER avec zone 1 |
| 18 | Single site cards | inline | Statut/Risque/Conso (scope=1 site) | GARDER — zone 2 conditionnel |
| 19 | Portfolio tabs + Sites table | inline | Tableau détaillé sites | REPLIER — zone 4 |
| 20 | Maturité modal | `Modal` | Détail maturité | OK — garder |

**Avant : 16+ sections visibles = scroll infini**
**Cible : 4 zones + "Voir plus" = 1 écran DG**

---

## 2. STRUCTURE CIBLE — 4 ZONES

### Zone 1 — PRIORITÉ (toujours visible, au-dessus du fold)
**Objectif** : en 5 secondes, le DG sait ce qui est critique

Fusionne : ExecutiveSummaryCard + HealthSummary + BriefingHeroCard + échéance

**Contenu** :
- Titre du problème #1 (ex: "Mise en conformité BACS requise")
- Impact financier (ex: "26 k€ d'exposition")
- Échéance (ex: "Échéance dépassée depuis le 1er janvier 2025")
- 1 CTA principal unique : "Voir conformité →"
- 2-3 lignes secondaires (alertes actives, sites à risque)

### Zone 2 — KPI DÉCIDEUR (toujours visible)
**Objectif** : vue chiffrée en 4 tuiles

Garde : ExecutiveKpiRow (4 tiles)
Conditionnel : Single site cards (si scope = 1 site)
Expert : ImpactDecisionPanel (sous les KPI)

### Zone 3 — ACTIONS RECOMMANDÉES (toujours visible, max 3)
**Objectif** : quoi faire maintenant

Fusionne : Watchlist items + Risque résiduel bloc + Briefing items
Format : 3 cartes action max avec impact + CTA

### Zone 4 — DÉTAIL (replié par défaut, "Voir plus ▼")
**Objectif** : détail pour l'utilisateur qui veut creuser

Contient (dans l'ordre) :
1. Top Sites (worst/best)
2. Market Context
3. Module Launchers
4. Data Activation
5. Essentials Row
6. Tableau Sites (multi-sites)
7. Data Quality (Expert)
8. Consistency (Expert)
9. Opportunities (Expert)

---

## 3. MAPPING ANCIEN → NOUVEAU

| Ancien bloc | Nouveau emplacement | Changement |
|-------------|---------------------|------------|
| ExecutiveSummaryCard | Zone 1 — intégré | Fusionné |
| HealthSummary | Zone 1 — intégré | Fusionné |
| BriefingHeroCard | Zone 1 — intégré | Fusionné |
| Échéance réglementaire | Zone 1 — intégré | Fusionné |
| ExecutiveKpiRow | Zone 2 — inchangé | Gardé |
| ImpactDecisionPanel | Zone 2 — Expert only | Gardé |
| Single site cards | Zone 2 — conditionnel | Gardé |
| Risque résiduel bloc | Zone 3 — fusionné | Fusionné |
| WatchlistCard | Zone 3 — fusionné | Fusionné |
| MarketContextCompact | Zone 4 — replié | Replié |
| OpportunitiesCard | Zone 4 — Expert | Replié |
| TopSitesCard | Zone 4 — replié | Replié |
| ModuleLaunchers | Zone 4 — replié | Replié |
| ConsistencyBanner | Zone 4 — Expert | Replié |
| DataQualityWidget | Zone 4 — Expert | Replié |
| DataActivationPanel | Zone 4 — replié | Replié |
| EssentialsRow | Zone 4 — replié | Replié |
| Sites table | Zone 4 — replié | Replié |

---

## 4. COMPOSANTS UI À UNIFIER

| Composant | Variantes actuelles | Cible |
|-----------|--------------------|-------|
| KpiCard | 4 styles (cockpit, patrimoine, conformité, facturation) | 1 seul `UnifiedKpiCard` |
| AlertBanner | 3 styles (Health, Watchlist, Consistency) | 1 seul `PriorityBanner` |
| ActionList | 3 styles (Briefing, Watchlist, Risque résiduel) | 1 seul `ActionList` |
| CTA Button | Bleu plein, bleu outline, orange, rouge | Primaire (bleu) + Secondaire (outline) |
| Heading | H1/H2/H3 inconstants | H1 page, H2 section, H3 sous-section |

---

## 5. QUICK WINS vs REFONTE

### Quick wins (effort S, impact immédiat)
1. **Replier zones 4+** derrière `useState(false)` + bouton "Voir le détail ▼"
2. **Fusionner HealthSummary dans ExecutiveSummaryCard** (supprimer le composant séparé)
3. **Masquer ModuleLaunchers** en non-Expert (c'est de la navigation, pas du cockpit)
4. **Masquer DataActivation** si tout est activé
5. **Supprimer le bloc Risque résiduel** (doublon de Zone 1 + Watchlist)

### Refonte structurante (effort M, semaine 2)
1. **Nouveau composant PriorityHero** : fusionne Summary + Health + Briefing + Échéance
2. **Nouveau composant ActionCards** : 3 actions max extraites de Watchlist + Opportunities
3. **Toggle "Analyse détaillée"** pour la zone 4

---

## 6. RÉSULTAT ATTENDU

### Avant
- 16+ sections
- Scroll : ~2500px
- Temps de compréhension : 30+ secondes
- CTA concurrents : 8+
- Doublons narratifs : 3 (Summary ≈ Briefing ≈ Watchlist)

### Après
- 3 zones + 1 repliée
- Scroll : ~800px (vue DG)
- Temps de compréhension : 5 secondes
- CTA principal : 1 unique
- Doublons : 0

### Critères d'acceptation
- [ ] DG comprend le risque principal en 5 secondes
- [ ] 1 seul CTA primaire visible
- [ ] Page 40% plus courte
- [ ] Aucun doublon de narration
- [ ] Mode Expert ajoute du détail sans casser la lisibilité
- [ ] Build OK, tests OK, aucune régression
