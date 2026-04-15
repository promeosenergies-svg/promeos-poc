# Audit UX/UI PROMEOS V2 — Complet (4 sprints)

**Date :** 2026-03-18
**Version auditée :** Post-Sprint 21 v4 (branche audit/flex-current-vision)
**Pages capturées :** 27
**Méthode :** Playwright headless + analyse visuelle

---

# SPRINT 1 — ACCUEIL + NAVIGATION

## Verdict
Le cockpit V3 est **nettement meilleur** que la version pré-audit. La structure 4 zones fonctionne : périmètre → priorité → KPI → actions. Mais la navigation latérale reste **peu lisible** avec des icônes sans labels (sauf au hover), et le breadcrumb `PROMEOS > Pilotage > Cockpit` est trop technique.

## Note /10

| Critère | Note |
|---------|------|
| Compréhension immédiate | 7/10 |
| Home utile | 7.5/10 |
| Navigation | 5.5/10 |
| Architecture de l'information | 6/10 |
| Clarté des libellés | 6.5/10 |
| Crédibilité enterprise | 7/10 |

## Top 10 problèmes

| # | Problème | Sévérité | Impact | Nature |
|---|----------|----------|--------|--------|
| 1 | Sidebar = icônes seules, aucun label visible sans hover | P1 | Fort | UX/navigation |
| 2 | Breadcrumb "PROMEOS > Pilotage > Cockpit" = jargon interne | P2 | Moyen | Contenu |
| 3 | "Maturité Plateforme 74%" = métrique opaque pour un DG | P2 | Moyen | Contenu |
| 4 | "Complétude Données 100%" semble trop optimiste | P2 | Moyen | Confiance |
| 5 | Zone basse "Analyse détaillée" repliée = invisible par défaut | P2 | Moyen | UX |
| 6 | Pas de date de dernière mise à jour visible sur le cockpit | P2 | Moyen | Confiance |
| 7 | 5 modules dans la sidebar sans regroupement clair | P2 | Moyen | Structure |
| 8 | Toggle "Expert" peu explicite (que change-t-il ?) | P3 | Faible | UX |
| 9 | Section "Administration" mélangée avec les modules métier | P3 | Faible | Structure |
| 10 | Scope switcher compact — on ne comprend pas toujours le périmètre actif | P2 | Moyen | UX |

## Quick wins
1. Ajouter des labels texte aux icônes sidebar (ou sidebar repliable avec labels)
2. Remplacer "Maturité Plateforme" par "Couverture opérationnelle"
3. Ajouter "Dernière analyse : il y a 2h" sur le cockpit

---

# SPRINT 2 — PATRIMOINE + CONFORMITÉ

## Verdict
La page Patrimoine est **dense et fonctionnelle**. Le registre patrimonial avec heatmap, compteurs et filtres est crédible. La conformité est **la meilleure brique du produit** — score, frise, obligations, urgences, parcours. Cependant, le lien patrimoine → conformité reste **implicite** (il faut naviguer, pas de CTA direct évident).

## Note /10

| Critère | Note |
|---------|------|
| Clarté des objets | 7/10 |
| Logique de structure | 7.5/10 |
| Qualité des fiches | 6.5/10 |
| Qualité des formulaires | 7/10 |
| Lisibilité conformité | 8/10 |
| Confiance / traçabilité visible | 7.5/10 |
| Cohérence patrimoine ↔ conformité | 6.5/10 |

## Top 12 problèmes

| # | Problème | Sévérité | Impact | Nature |
|---|----------|----------|--------|--------|
| 1 | Heatmap "Top sites à risque" = 3 cartes + 2 pastilles = layout incohérent | P1 | Fort | UI |
| 2 | "Risque global 313 k€" vs "26 k€ risque financier" = confusion métriques | P1 | Fort | Contenu |
| 3 | Tableau patrimoine : colonnes "Risque (k€)" et "NC conformité" trop similaires | P2 | Moyen | UI |
| 4 | Badge "Évaluation en attente" = pas assez actionnable | P2 | Moyen | UX |
| 5 | Conformité : parcours 5 étapes (CEE retiré) mais "Plan d'action" = en cours → pas de visibilité sur blockers | P2 | Moyen | UX |
| 6 | Score 86/100 avec "1 non conforme" semble contradictoire sans explication | P2 | Moyen | Confiance |
| 7 | Frise réglementaire compacte — texte trop petit en résolution standard | P2 | Moyen | UI |
| 8 | Page OPERAT/Tertiaire : "6 EFA enregistrées" mais aucun statut de qualité visible | P2 | Moyen | Confiance |
| 9 | Obligations KB (Intelligence KB) en bas de conformité = pas clair si c'est validé ou suggéré | P3 | Faible | Contenu |
| 10 | Patrimoine → Conformité : aucun deep-link contextuel depuis le tableau sites | P2 | Moyen | Workflow |
| 11 | "Confiance : Données partielles" visible mais pas d'explication de ce qui manque | P2 | Moyen | Confiance |
| 12 | FlexPotentialCard monté dans la fiche site — bon mais sans contexte explicatif | P3 | Faible | UX |

## Quick wins
1. Unifier les métriques risque (1 seul chiffre par scope)
2. Deep-link "Voir conformité" depuis chaque ligne du tableau sites
3. Ajouter tooltip "Ce score exclut..." sur le score conformité

---

# SPRINT 3 — FACTURE + ACHAT ÉNERGIE

## Verdict
La page Facturation est **la plus opérationnelle** — anomalies clairement colorées, montants lisibles, CTA "Voir détail" par anomalie. Le shadow billing (674,47 € d'écart affiché) est un vrai différenciateur. La page Achat Énergie est **impressionnante** : scénarios Prix Fixe / Indexé / Spot comparés côte à côte avec le tag "Recommandé". C'est le point fort absolu du produit.

## Note /10

| Critère | Note |
|---------|------|
| Lisibilité facture | 8/10 |
| Exploitabilité des tableaux | 7.5/10 |
| Clarté des anomalies | 8.5/10 |
| Qualité décisionnelle | 8.5/10 |
| Cohérence facture ↔ achat | 7/10 |
| Crédibilité métier | 8/10 |
| Actionnabilité | 7.5/10 |

## Top 12 problèmes

| # | Problème | Sévérité | Impact | Nature |
|---|----------|----------|--------|--------|
| 1 | Transition Facturation → Achat = 2 modules séparés dans la sidebar, pas de CTA direct | P1 | Fort | Workflow |
| 2 | Anomalies facture : badges "Moyen" / "Élevé" sans explication du calcul de sévérité | P2 | Moyen | Confiance |
| 3 | Shadow billing "674,47 €" écart affiché mais pas d'explication de la méthode | P2 | Moyen | Confiance |
| 4 | Tableau factures : colonne "Statut" = "Auditée" sans date d'audit ni acteur | P2 | Moyen | Traçabilité |
| 5 | Page Achat : "Budget prévisionnel à 78% du cours proposé" = phrase dense | P3 | Faible | Contenu |
| 6 | Scénario "Recommandé" sur Prix Fixe — pas de justification visible | P2 | Moyen | Confiance |
| 7 | CTA "Clore mon achat" en bas — trop engageant sans confirmation explicite | P2 | Moyen | UX |
| 8 | TariffWindowsCard monté mais vide si aucune grille TURPE 7 configurée | P2 | Moyen | UX |
| 9 | Renouvellements : pas visible depuis Facturation, nécessite navigation séparée | P3 | Faible | Workflow |
| 10 | Historique factures : pas de filtre par fournisseur | P3 | Faible | UX |
| 11 | Réconciliation mentionnée mais pas visible directement | P2 | Moyen | Workflow |
| 12 | "Exporter CSV" et "Importer CSV" au même niveau = risque de confusion | P3 | Faible | UX |

## Quick wins
1. Ajouter "Pourquoi recommandé ?" en lien sous le tag Recommandé
2. Ajouter un CTA "Optimiser l'achat" depuis la page Facturation
3. TariffWindowsCard : afficher "Configurez vos fenêtres tarifaires" au lieu de rien

---

# SPRINT 4 — PARAMÉTRAGE + DESIGN SYSTEM + COHÉRENCE GLOBALE

## Verdict
L'admin Utilisateurs est **propre et lisible** — rôles colorés, statuts clairs, scopes visibles. Le design system est **cohérent à 80%** mais avec des dérives entre modules (tailles de police, espacements, styles de badges). L'ensemble donne une impression de **produit sérieux** mais avec des **traces de développement incrémental** (densité variable, certaines sections vides).

## Note /10

| Critère | Note |
|---------|------|
| Paramétrage | 7/10 |
| Rôles / confiance visible | 8/10 |
| Cohérence visuelle | 6.5/10 |
| Design system | 6/10 |
| Robustesse des états UX | 6/10 |
| Cohérence inter-modules | 6.5/10 |
| Qualité perçue globale | 7/10 |
| Crédibilité enterprise finale | 7/10 |

## Top 15 problèmes finaux

| # | Problème | Sévérité | Impact |
|---|----------|----------|--------|
| 1 | Sidebar sans labels = navigation par devinette | P1 | Fort |
| 2 | 3 styles de KPI cards différents entre cockpit, patrimoine et conformité | P1 | Fort |
| 3 | Métriques risque incohérentes entre pages | P1 | Fort |
| 4 | Aucun empty state standardisé (certains vides, certains avec message) | P2 | Moyen |
| 5 | Plan d'actions : priorité/impact visible mais pas de timeline | P2 | Moyen |
| 6 | Score conformité "86/100" vs "1 NC" = contradiction non expliquée | P2 | Moyen |
| 7 | Toggle Expert sans explication de ce qu'il ajoute/retire | P2 | Moyen |
| 8 | Badges hétérogènes (taille, border-radius, couleur) entre modules | P2 | Moyen |
| 9 | Flex components montés mais sans onboarding/explication | P2 | Moyen |
| 10 | Pas de date/heure "dernière synchro" visible | P2 | Moyen |
| 11 | Page Actions : "Impact estimé" sans unité explicite sur certaines lignes | P2 | Moyen |
| 12 | Administration en bas de sidebar = facile à rater | P3 | Faible |
| 13 | Notifications : badge "7" sans breakdown visible | P3 | Faible |
| 14 | Breadcrumb trop technique | P3 | Faible |
| 15 | Zones de texte descriptif trop longues dans certains KPI cards | P3 | Faible |

---

# SYNTHÈSE GLOBALE FINALE

## 1. Verdict exécutif

PROMEOS est un **vrai produit B2B opérationnel**, pas une démo. La chaîne patrimoine → conformité → facturation → achat est **fonctionnelle et cohérente**. Les briques conformité et achat énergie sont **au-dessus de la moyenne** du marché. Le cockpit V3 est lisible et orienté action.

**Forces :**
- Conformité réglementaire = meilleure brique (frise, parcours, urgences, score)
- Achat énergie = différenciateur (3 scénarios comparés, tag Recommandé)
- Facturation = opérationnel (anomalies colorées, shadow billing)
- Action center = complet (workflow, audit trail, recommandations)

**Faiblesses :**
- Navigation = le point noir (sidebar icônes seules)
- Design system = 80% cohérent, 20% patchwork
- Métriques risque = incohérentes entre vues
- Empty states = non standardisés
- Flex = monté mais sans contexte

## 2. Note globale /10

| Critère | Note |
|---------|------|
| Compréhension immédiate | 7/10 |
| Architecture produit | 7/10 |
| Navigation | 5.5/10 |
| Patrimoine | 7/10 |
| Conformité | 8/10 |
| Facture | 8/10 |
| Achat énergie | 8.5/10 |
| Formulaires | 7/10 |
| Tableaux | 7.5/10 |
| Design system | 6/10 |
| Cohérence globale | 6.5/10 |
| Crédibilité enterprise | 7/10 |
| **Moyenne** | **7.1/10** |

## 3. Top 25 problèmes

| # | Problème | Module | P | Impact | Correction |
|---|----------|--------|---|--------|------------|
| 1 | Sidebar sans labels | Navigation | P1 | Critique | Labels + sidebar repliable |
| 2 | 3 styles KPI cards | Global | P1 | Fort | 1 composant KpiCard unique |
| 3 | Métriques risque incohérentes | Patrimoine/Cockpit | P1 | Fort | 1 source de vérité risque |
| 4 | Transition Facture → Achat cassée | Workflow | P1 | Fort | CTA "Optimiser l'achat" |
| 5 | Heatmap layout incohérent | Patrimoine | P1 | Fort | Cards uniformes ou treemap |
| 6 | Score 86 + "1 NC" contradictoire | Conformité | P2 | Moyen | Tooltip explication |
| 7 | Empty states non standardisés | Global | P2 | Moyen | Composant EmptyState |
| 8 | Toggle Expert opaque | Cockpit | P2 | Moyen | Badge "+ détails experts" |
| 9 | Shadow billing sans méthode visible | Facture | P2 | Moyen | Lien "Comment c'est calculé" |
| 10 | Badges hétérogènes | Design system | P2 | Moyen | Normaliser tailles/couleurs |
| 11 | "Recommandé" sans justification | Achat | P2 | Moyen | Lien "Pourquoi ?" |
| 12 | Pas de dernière synchro visible | Cockpit | P2 | Moyen | Timestamp footer |
| 13 | Deep-link patrimoine → conformité absent | Workflow | P2 | Moyen | CTA par ligne tableau |
| 14 | Plan d'actions sans timeline | Actions | P2 | Moyen | Gantt ou dates visibles |
| 15 | Flex components sans onboarding | Flex | P2 | Moyen | Tooltip "Qu'est-ce que c'est ?" |
| 16 | Frise réglementaire texte petit | Conformité | P2 | Moyen | Zoom/responsive |
| 17 | KB Intelligence = pas clair si validé ou suggéré | Conformité | P2 | Moyen | Badge "Suggestion IA" |
| 18 | TariffWindowsCard vide sans grille | Achat | P2 | Moyen | Message explicite |
| 19 | Breadcrumb trop technique | Navigation | P3 | Faible | Simplifier |
| 20 | "Maturité Plateforme" opaque | Cockpit | P2 | Moyen | Renommer |
| 21 | "Complétude 100%" trop optimiste | Cockpit | P2 | Moyen | Nuancer |
| 22 | Notifications badge sans breakdown | Actions | P3 | Faible | Breakdown au hover |
| 23 | Admin en bas sidebar | Navigation | P3 | Faible | Séparer visuellement |
| 24 | "Clore mon achat" trop engageant | Achat | P2 | Moyen | Confirmation modale |
| 25 | Colonnes factures sans filtre fournisseur | Facture | P3 | Faible | Ajouter filtre |

## 4. Ce qui décrédibilise le plus PROMEOS
1. La sidebar sans labels = sensation d'app mobile, pas de cockpit enterprise
2. Les métriques risque incohérentes = le même sujet donne des chiffres différents
3. Les empty states = zones vides sans explication = impression d'app incomplète

## 5. Ce qui manque pour être world-class
1. Navigation avec labels + raccourcis clavier
2. Design system unifié (1 KpiCard, 1 Badge, 1 EmptyState)
3. Méthode de calcul visible sur chaque KPI (info-bulle)
4. Timeline / Gantt dans le plan d'actions
5. Onboarding contextuel sur les nouvelles briques (flex)

## 6. Plan d'action 30 jours

| Semaine | Actions |
|---------|---------|
| S1 | Sidebar labels + KpiCard unique + métriques risque unifiées |
| S2 | EmptyState composant + deep-links patrimoine→conformité + toggle Expert |
| S3 | Shadow billing méthode visible + "Pourquoi recommandé" achat + frise zoom |
| S4 | Badges normalisés + Flex onboarding + dernière synchro visible |

## 7. Top 5 actions finales

| # | Action | Effort | Owner | Deadline | Impact |
|---|--------|--------|-------|----------|--------|
| 1 | Sidebar avec labels texte | S | Front | S1 | Crédibilité navigation |
| 2 | 1 composant KpiCard unifié | M | Front | S1 | Cohérence visuelle |
| 3 | Unifier métriques risque (1 chiffre/scope) | S | Full-stack | S1 | Confiance données |
| 4 | EmptyState composant standardisé | S | Front | S2 | Robustesse perçue |
| 5 | CTA "Optimiser l'achat" depuis Facturation | S | Front | S2 | Continuité workflow |
