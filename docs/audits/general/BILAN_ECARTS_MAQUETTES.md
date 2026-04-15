# Bilan des écarts — Maquettes vs Implémentation
**Date** : 2026-03-24
**Branches** : `feat/cockpit-world-class` + `fix/migrate-calc-to-backend`

---

## Facteur CO₂ — Vérification triple source

| Source | Valeur | Fichier |
|--------|--------|---------|
| ADEME Base Empreinte V23.6 | **0.052** kgCO₂e/kWh | `config/emission_factors.py:25` |
| Test P0 assertion | `== 0.052` | `test_cockpit_p0.py:170` |
| Note dans emission_factors.py | "0.0569 non retrouvé dans aucune source ADEME actuelle" | `emission_factors.py:15` |

**Conclusion** : `0.052` est le facteur canonique. Le `0.0569` (ancien sprint) a été **reverté** dans `ConsumptionExplorerPage.jsx` et les commentaires corrigés.

---

## Vue Exécutive (/cockpit) — Mode non-expert

| Widget maquette | Statut | Écart restant |
|-----------------|--------|---------------|
| Tabs (Vue exec / Tableau de bord) | ✅ EXACT | — |
| 4 KPI cards (Score/Risque/Réduction/Actions) | ✅ EXACT | Card 2 amber quand risque > 0 ✓ |
| Bannière retard trajectoire | ✅ EXACT | Montant + deadline + CTA |
| 2-col Alertes + Événements | ✅ EXACT | 3 alertes + 4 événements |
| Courbe trajectoire DT | ✅ EXACT* | *Données 2024-2030 (maquette montre 2020-2030 mais ref_year=2024 en démo) |
| 2-col Performance sites + Vecteur | ✅ EXACT | Couleurs par site ✓, CO₂ scopes backend ✓ |
| Actions Impact | ✅ EXACT | Barre verte ✓, footer toujours visible ✓ |
| Scope indicator visible | ✅ CORRIGÉ | Expert-only (masqué en non-expert) |
| Sections legacy visibles | ✅ CORRIGÉ | Expert-only (ExecKpiRow, topActions, detail zone) |

### Écarts visuels restants (mineurs)

| Écart | Détail | Impact |
|-------|--------|--------|
| Trajectoire ref_year | Maquette montre 2020, démo seed commence 2024 | Donnée (pas un bug code) |
| `projection_mwh` vide | Backend retourne `[]` (pas d'actions liées à la trajectoire) | Feature à coder (sprint suivant) |
| Maquette montre "8 / 23" actions | Démo a 5 / 12 (données réelles seed) | Correct — on affiche la vérité |
| Maquette montre "142 k€" risque | Démo montre ~70 k€ (26k régl + 44k billing) | Correct — données réelles |

---

## Vue Exploitation (/) — Mode non-expert

| Widget maquette | Statut | Écart restant |
|-----------------|--------|---------------|
| Tabs | ✅ EXACT | — |
| 4 KPI J-1 | ⚠️ PARTIEL | 2 sur 4 montrent "—" (données manquantes, pas de bug) |
| Conso 7j BarChart | ✅ EXACT | Recharts BarChart |
| Profil J-1 AreaChart | ✅ EXACT | Recharts + seuil conditionnel |
| Trajectoire + Actions 2-col | ✅ CORRIGÉ | Placeholder si null + 2 colonnes |
| Sites J-1 vs Baseline | ⚠️ PARTIEL | `consoJ1BySite` prop non passée (barres vides) |
| ModuleLaunchers | ✅ EXACT | — |
| Sections legacy masquées | ✅ CORRIGÉ | HealthSummary, BriefingHeroCard, EssentialsRow, Sites risque |

### Écarts fonctionnels restants

| Écart | Cause | Solution (sprint suivant) |
|-------|-------|---------------------------|
| KPI "Conso ce mois" = "—" | Pas d'endpoint dédié | Query `ConsumptionTarget` monthly avec `actual_kwh` |
| KPI "CO₂ réseau" = "—" | Connecteur RTE eco2mix non branché | Intégrer API RTE |
| Sites Baseline vides | `consoJ1BySite` jamais passé en prop | Calculer depuis `weekSeries` par site |
| Profil J-1 "indisponible" | Pas de données hourly dans le scope EMS | Vérifier seed + filtre granularity |

---

## Violations architecture éliminées (ce sprint)

| Violation | Avant | Après | Commit |
|-----------|-------|-------|--------|
| `Cockpit.jsx` `pctConf = conformes/total*100` | Calcul front | `cockpitKpis.conformiteScore` (RegAssessment) | `2dc28d0` |
| `VecteurEnergetiqueCard` agrège CO₂ per-site | `reduce()` front | `data.vectors[]`, `data.scope1_t_co2` backend | `2dc28d0` |
| `CreateActionModal/Drawer` `* 0.052` | Calcul front | Supprimé (backend post-création) | `2dc28d0` |
| `ConsumptionExplorerPage` `* 0.052` → `0.0569` | **Bug introduit puis corrigé** | Reverté à `0.052` (ADEME V23.6) | `136325c` |

---

## Compteurs finaux

| Métrique | Valeur |
|----------|--------|
| Tests backend | **13/13** (cockpit P0) + **33/33** (emissions) |
| Tests frontend | **137/139** (2 pre-existing inchangés) |
| Régressions | **0** |
| Violations `* 0.052` front production | **0** (supprimées des modals, conservées dans constants.js + ConsumptionExplorer comme valeur canonique) |
| Violations `conformes/total*100` dans Cockpit.jsx | **0** (migré vers RegAssessment) |
| Widgets EXACT MATCH vs maquette | **14/18** |
| Widgets PARTIEL (données manquantes) | **4/18** |
| Widgets MISSING | **0** |
