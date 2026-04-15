# AUDIT UX/UI COMPLET — PROMEOS
**Date** : 2026-03-16
**Auditeur** : Principal UX Auditor / Lead Product Critic
**Périmètre** : toutes les briques sauf consommation/performance/ACC
**Pages auditées** : 27 (captures Playwright)

---

## 1. VERDICT EXÉCUTIF

PROMEOS est un POC fonctionnel impressionnant par sa couverture (patrimoine, conformité, facturation, achat énergie, actions, alertes, admin), mais qui souffre de **fragmentation perceptuelle**. Chaque écran pris isolément est correct voire bon. L'ensemble manque d'une colonne vertébrale UX unique, d'une hiérarchie d'information constante et d'un design system stabilisé.

Le cockpit est trop long et trop dense. Le patrimoine est fonctionnel mais hétérogène. La conformité est la brique la plus aboutie. La facturation est prometteuse mais patchwork. L'admin est propre mais vide.

**Verdict** : crédible pour une démo qualifiée, pas encore pour un contrat enterprise signé sans accompagnement.

**Note globale : 6.2 / 10**

---

## 2. NOTES DÉTAILLÉES /10

| Axe | Note | Commentaire |
|-----|------|-------------|
| Compréhension immédiate | 6/10 | Cockpit dense, on ne sait pas par où commencer |
| Architecture produit | 7/10 | Bonne couverture, bonne séparation des briques |
| Navigation | 6/10 | Sidebar claire mais changements de contexte mal signalés |
| Clarté métier | 7/10 | Vocabulaire B2B France correct, quelques anglicismes |
| Qualité des parcours | 5/10 | Parcours créés en sprint, ruptures entre modules |
| Qualité des écrans | 7/10 | Individuellement bons, globalement hétérogènes |
| Qualité des formulaires | 6/10 | Quick-create bon, wizard avancé lourd |
| Exploitabilité tableaux | 7/10 | Patrimoine et Actions bien structurés |
| Cohérence visuelle | 5/10 | Design system fragmenté, 3-4 styles coexistent |
| Crédibilité enterprise | 6/10 | Correcte mais pas encore premium |
| Confiance / traçabilité | 7/10 | Conformité très bien, reste faible ailleurs |
| Cohérence globale | 5/10 | Briques juxtaposées, pas un produit unifié |

---

## 3. TOP 25 PROBLÈMES

| # | Problème | Module | Sév | Impact | Correction |
|---|----------|--------|-----|--------|------------|
| 1 | Cockpit trop long — 15+ sections, scroll infini | Cockpit | P1 | Critique | Réduire à 4 blocs, mode expert = détail |
| 2 | Pas de home par rôle | Global | P1 | Fort | Landing contextuel DG vs Energy Manager |
| 3 | Scope switcher ambigu — site vs org | Header | P1 | Critique | Indicateur visuel fort du scope actif |
| 4 | Heatmap patrimoine peu lisible | Patrimoine | P2 | Moyen | Treemap cliquable |
| 5 | "ROI 28%" dans Actions = trompeur | Actions | P1 | Fort | Renommer "Taux de réalisation" |
| 6 | Colonnes vides dans Actions (CO₂e, Responsable) | Actions | P2 | Moyen | Masquer si aucune donnée |
| 7 | Alertes sans action inline | Alertes | P2 | Moyen | CTA contextuel par alerte |
| 8 | Frise conformité trop compacte | Conformité | P2 | Moyen | Responsive + zoom |
| 9 | Mémobox état vide — tags cliquables sans résultat | KB | P2 | Moyen | Afficher résultats au clic |
| 10 | Segmentation sans feedback immédiat | Segmentation | P2 | Moyen | Score en temps réel |
| 11 | Connectors "Synchroniser" sans feedback | Admin | P2 | Moyen | Toast + timestamp sync |
| 12 | Activation données — écran mort si tout vert | Admin | P3 | Faible | Masquer ou ajouter maintenance |
| 13 | Anomalies facture incompréhensibles pour non-expert | Bill Intel | P1 | Fort | Tooltip explicatif |
| 14 | Mois "Manquant" en rouge sans CTA | Billing | P2 | Moyen | CTA "Importer cette facture" |
| 15 | Scénarios achat sans détail hypothèses | Achat | P1 | Fort | Détail modèle visible |
| 16 | Assistant achat 8 étapes sans sauvegarde | Achat | P2 | Moyen | Auto-save brouillon |
| 17 | "Profil à 30%" non expliqué | Achat | P2 | Moyen | Tooltip explicatif |
| 18 | Onboarding 6/6 reste visible | Admin | P3 | Faible | Auto-masquer |
| 19 | 3-4 styles de cartes KPI coexistent | Design | P1 | Fort | Unifier KpiCard |
| 20 | Densité informationnelle inégale | Design | P2 | Moyen | Normaliser |
| 21 | Breadcrumb non actionnable partout | Navigation | P2 | Moyen | Breadcrumb cliquable unifié |
| 22 | Mode Expert — pas clair ce qui change | Header | P2 | Moyen | Indicateur "N éléments Expert" |
| 23 | Footer ADMINISTRATION sur toutes les pages | Nav | P3 | Faible | Intégrer dans sidebar |
| 24 | Pas d'export PDF natif (sauf Actions) | Global | P2 | Moyen | PDF sur Cockpit + Conformité |
| 25 | Pas de dark mode | Design | P3 | Faible | Post-V2 |

---

## 4. AUDIT PAR MODULE

### Cockpit
- **Forces** : résumé exécutif, KPI conformité, leviers activables, prochaine échéance
- **Faiblesses** : 15+ blocs = scroll infini, mélange vue décideur/opérationnelle, heatmap illisible
- **Manque** : version condensée 3-blocs pour DG, landing par rôle

### Actions & Suivi
- **Forces** : tableau structuré, filtres, avancement global
- **Faiblesses** : "ROI" trompeur, colonnes vides, pas de Kanban
- **Manque** : assignation rapide, dépendances, rappels

### Notifications / Alertes
- **Forces** : compteur critique/warning, tableau avec source
- **Faiblesses** : aucune action inline, pas de groupement
- **Manque** : filtrage 1-clic par criticité, action bulk

### Patrimoine
- **Forces** : registre structuré, risque global, filtres présets, profil énergie
- **Faiblesses** : heatmap peu lisible, confusion scope, compteurs incohérents
- **Manque** : vue arborescente, carte géographique

### Conformité ★ Meilleure brique
- **Forces** : score breakdown, frise, 3 obligations structurées, statuts prudents, KB
- **Faiblesses** : confusion scope (corrigé), dates ISO (corrigé)
- **Manque** : vue portfolio comparée, export PDF dossier

### Facturation / Bill Intel
- **Forces** : anomalies avec montants, shadow billing, chronologie mensuelle
- **Faiblesses** : anomalies incompréhensibles pour non-expert, mois "Manquant" sans CTA
- **Manque** : tooltip explicatif, import contextuel, réconciliation guidée

### Achat Énergie
- **Forces** : 3 scénarios comparés, recommandation, CTA
- **Faiblesses** : hypothèses opaques, "Budget autorisé 150%" non expliqué
- **Manque** : détail modèle calcul, historique simulations

### Assistant Achat
- **Forces** : wizard 8 étapes, sélection périmètre claire
- **Faiblesses** : pas de sauvegarde intermédiaire
- **Manque** : auto-save, résumé choix par étape

### Renouvellements
- **Forces** : tableau clair, filtres temporels, indexation visible
- **Faiblesses** : "Profil 30%" non expliqué
- **Manque** : alertes email sur contrats expirants

### Admin (Users, Onboarding, Connectors, Activation, Status)
- **Forces** : propre, clair, rôles visibles
- **Faiblesses** : onboarding figé, connectors sans feedback, activation = page morte
- **Manque** : CRUD complet utilisateurs, audit log

### Mémobox / KB
- **Forces** : concept base de connaissances, tags, recherche
- **Faiblesses** : état vide, tags sans résultat, "Mode démo" visible
- **Manque** : contenu structuré, résultats au clic

### Segmentation B2B
- **Forces** : questionnaire pertinent, badges réponses
- **Faiblesses** : aucun feedback temps réel
- **Manque** : résultat immédiat, recommandation

---

## 5. RUPTURES DE PARCOURS

1. **Cockpit → Action** : CTA "Créer action" ouvre drawer mais liste actions sur autre page
2. **Cockpit → Conformité** : scope change silencieusement (1 site vs all)
3. **Patrimoine → Conformité** : aucun lien direct site → fiche conformité
4. **Conformité → OPERAT** : "Ouvrir OPERAT" va à la liste EFA, pas à l'EFA du site
5. **Alertes → Source** : lien "Source" ne navigue nulle part
6. **Facture → Anomalie → Action** : CTA redirige vers formulaire générique, pas prérempli
7. **Achat → Renouvellements** : pas de lien simulation ↔ contrat à renouveler
8. **Admin Import** : accessible depuis sidebar Admin ET Patrimoine — doublon
9. **KB tags → Résultats** : tags cliquables mais rien ne se passe
10. **Onboarding 6/6 → Next** : pas de redirection automatique vers cockpit

---

## 6. DÉFAUTS DESIGN SYSTEM

| Catégorie | Problème |
|-----------|----------|
| Cartes KPI | 4 styles différents selon les modules |
| Badges | 5 tailles non normalisées |
| Boutons CTA | Bleu plein, bleu outline, orange, rouge — pas de règle |
| Espacement | Dense (patrimoine) vs vide (KB) — inconstant |
| Tableaux | Triables sur certaines pages, non triables sur d'autres |
| Icônes | Mix Lucide + custom, tailles 14-20px variables |
| Couleurs statut | 3 nuances de vert "conforme" différentes |
| Titres | H1/H2 styles différents selon les pages |
| Modales | Drawer droit, modale centrée, drawer plein — 3 patterns |

---

## 7. IMPRESSIONS DE DÉMO / PRODUIT FRAGILE

1. Onboarding 6/6 figé — page morte visible
2. "Mode démo — données locales" dans la KB
3. Colonnes vides partout (CO₂e, Responsable)
4. "Profil à 30%" sans explication
5. Heatmap avec 5 sites — ne démontre pas l'échelle
6. "PROMEOS v1.7" et "447 endpoints API" exposés
7. Scope switcher qui change les données sans feedback

---

## 8. GAP VERS WORLD-CLASS

| Gap | Existant | World-class |
|-----|----------|-------------|
| Vue par rôle | 1 cockpit pour tous | Landing adapté par rôle |
| Design system | 3-4 styles | 1 design system documenté |
| Workflow guidé | CTA isolés | Parcours bout en bout |
| Export | CSV uniquement | PDF, Excel, PowerPoint |
| Personnalisation | Aucune | Dashboards configurables |
| Mobile | Non responsive | PWA responsive |
| Multi-langue | FR uniquement | FR + EN |
| Aide contextuelle | Aucune | Tooltips, tours guidés |
| SSO/SAML | Non | Requis enterprise |

---

## 9. PLAN D'ACTION 30 JOURS

### Semaine 1 — Quick wins critiques
| Action | Impact | Effort | Priorité |
|--------|--------|--------|----------|
| Cockpit condensé 4 blocs | Critique | M | P0 |
| "ROI" → "Taux de réalisation" | Fort | S | P0 |
| Masquer colonnes vides Actions | Moyen | S | P1 |
| Masquer onboarding si 6/6 | Faible | S | P1 |

### Semaine 2 — Cohérence
| Action | Impact | Effort | Priorité |
|--------|--------|--------|----------|
| Unifier KpiCard (1 seul style) | Fort | M | P1 |
| CTA inline sur alertes | Moyen | M | P1 |
| Tooltip anomalies facture | Fort | S | P1 |
| Feedback "Synchroniser" Connectors | Moyen | S | P2 |

### Semaine 3 — Parcours
| Action | Impact | Effort | Priorité |
|--------|--------|--------|----------|
| Lien Patrimoine site → Conformité | Fort | S | P1 |
| Scope indicator visuel fort | Critique | M | P1 |
| CTA "Importer facture" mois manquant | Moyen | S | P2 |
| Breadcrumb cliquable unifié | Moyen | M | P2 |

### Semaine 4 — Polish
| Action | Impact | Effort | Priorité |
|--------|--------|--------|----------|
| Masquer "Mode démo" et "447 endpoints" | Moyen | S | P2 |
| Normaliser badges/boutons/icônes | Fort | M | P2 |
| Auto-save brouillon assistant achat | Moyen | M | P2 |
| Export PDF cockpit + conformité | Fort | M | P2 |

---

## 10. TOP 5 ACTIONS FINALES

| # | Action | Effort | Owner | Deadline | Impact |
|---|--------|--------|-------|----------|--------|
| 1 | **Cockpit condensé** : 4 blocs max, reste en "voir plus" / Expert | M | Front | S1 | DG voit l'essentiel en 5s |
| 2 | **Scope indicator** : badge permanent "1 site / 5 sites / Org" | S | Front | S1 | Élimine 50% des confusions |
| 3 | **Design system unifié** : 1 KpiCard, 1 Badge, 1 Button, 1 Drawer | M | Front | S2-S3 | Passe de "sprints assemblés" à "produit" |
| 4 | **Parcours bout en bout** : site → conformité → action → preuve | M | Full | S2-S3 | Prouve un vrai cockpit de travail |
| 5 | **Tooltips contextuels** : 1 phrase d'explication sur chaque KPI/anomalie/score | S | Front | S3-S4 | Non-expert comprend chaque nombre |
