# AUDIT TOTAL PROMEOS — V3 (10 mars 2026)

**Quatuor d'experts** : Lead Product Auditor · UX/UI Principal · Functional QA · Senior Architect
**Méthode** : Playwright headless 1920×1080 (27 pages + 8 interactions) + analyse code source
**Seed** : Helios S (5 sites, 36 factures, 12 actions)
**Version** : PROMEOS v1.0 — post-sprint P0/P1

---

## 1. Executive Summary

| | |
|---|---|
| **Note globale** | **74 / 100** |
| **Verdict** | Produit crédible pour une démo structurée, pas encore pour une démo free-roam où le prospect explore seul |
| **Maturité réelle** | Late-beta avancé — solide sur la profondeur fonctionnelle, fragile sur la cohérence de surface |
| **Potentiel après corrections P0** | **82–85 / 100** |

### 5 risques les plus graves

| # | Risque | Impact |
|---|--------|--------|
| R1 | **Onboarding 0/6** malgré données seedées — perte de crédibilité immédiate si prospect voit la page | Confiance |
| R2 | **Connecteurs "(stub)"** visibles — 3 sur 5 affichent "stub" dans la description | Crédibilité |
| R3 | **Activation montre 1 seul site** sur 5 — donne l'impression que la plateforme n'a qu'un site | Crédibilité |
| R4 | **52 anomalies billing pour 36 factures** — shadow_gap fire sur quasi toutes les factures | Plausibilité |
| R5 | **Diagnostic : 50+ lignes de compteurs dupliqués** — même site×type dupliqué 4-6 fois, illisible | QA/Densité |

### 5 forces réelles

| # | Force |
|---|-------|
| F1 | **Module Achat complet** — simulation, scoring 42/100, recommandation TH Solaires, 4 offres comparées, workflow 8 étapes |
| F2 | **Bill Intelligence riche** — shadow billing décomposé, drawer explainability, 14 règles, confiance affichée |
| F3 | **Heatmap usages 7×24** — profil comportemental, score 99, talon/pointe/facteur de charge lisibles |
| F4 | **Patrimoine structuré** — heatmap sites, risque global 266 k€, frameworks affichés, drawer site fonctionnel |
| F5 | **Navigation contextuelle** — sidebar change par module, breadcrumbs cohérents, scope switcher fonctionnel |

---

## 2. Notes détaillées par dimension

| Dimension | Note | Commentaire sévère |
|-----------|------|-------------------|
| **UX** | 72 | Parcours cockpit→action clair, mais trop de pages "expert" sans onboarding. Le prospect hésite après le cockpit |
| **UI** | 76 | Design system cohérent (cards, badges, couleurs), mais densité trop forte sur Bill Intel et Diagnostic |
| **Navigation** | 78 | Sidebar contextuelle excellente, mais 8 pages cachées accessibles uniquement via Ctrl+K |
| **Scope / Gouvernance** | 70 | Scope switcher fonctionne, mais scope "Siege HELIOS Paris" affiché partout même quand l'info est org-level |
| **KPI / Calcul** | 65 | Score conformité 59/100 vs cockpit, actions score binaire 55/80, readiness dépend d'un placeholder |
| **Facturation / Achat** | 80 | Meilleur module. Shadow billing décomposé, drawer riche, 4 scénarios achat avec scoring |
| **Workflow / Actionability** | 68 | Cockpit liste 5 actions prioritaires avec "Créer une action", mais pas de passage direct anomalie→action |
| **Demo credibility** | 66 | Onboarding 0/6, connectors "(stub)", activation 1 site, diagnostic illisible — cassent la confiance |
| **Architecture visible** | 75 | Pas de localhost, pas de leak API, status page 7/7 OK, footer v1.0 propre |
| **Wording / Microcopy** | 73 | Labels FR corrects, mais "Rechercher\u2026" unicode visible dans Activation, "Brique 3 — Post-ARENH v3.0" technique |
| **Responsive / Densité** | 67 | Bill Intel : 20+ cards d'anomalies en scroll infini. Diagnostic : 50+ lignes. Pas de pagination |
| **Product story** | 72 | Le cockpit raconte une histoire (scoring, alertes, actions), mais la suite est trop fragmentée |

---

## 3. Top problèmes critiques

| ID | Problème | Zone | Pourquoi c'est grave | P | Effort | Type |
|----|----------|------|---------------------|---|--------|------|
| C01 | **Onboarding 0/6** après seed — race condition API | Onboarding | Un prospect voit "0%" et pense que rien n'est configuré | P0 | S | Technique |
| C02 | **3 connecteurs "(stub)"** visibles sur la page Connexions | Connectors | Signal POC immédiat — "Enedis Open Data (stub)" | P0 | XS | Wording |
| C03 | **Activation montre 1 site** au lieu de 5 | Activation | Impression de plateforme vide | P0 | S | Data |
| C04 | **52 anomalies billing / 36 factures** — shadow_gap omniprésent | Bill Intel | "Toutes vos factures sont anomaliques" = non crédible | P0 | M | Calcul |
| C05 | **Diagnostic : 50+ lignes** de compteurs dupliqués sans pagination | Diagnostic | Page illisible, impression de dump technique | P1 | S | UX |
| C06 | **Energy Copilot vide** — "0 propositions, lancez l'analyse" | Copilot | Page visible dans sidebar, totalement vide | P1 | XS | Démo |
| C07 | **Mémobox 0 items** — base de connaissances vide | KB | Page accessible, aucun contenu seedé | P1 | S | Data |
| C08 | **Score actions binaire** 55/80 (hardcodé) — pas corrélé aux vraies actions | Cockpit | KPI trompeur, pas défendable si on pose la question | P1 | M | KPI |
| C09 | **Renouvellements : 2 contrats, même site** — Engie + EDF sur Siege Paris | Renouv. | Un site avec 2 fournisseurs ? Suspect en démo | P1 | S | Data |
| C10 | **Conformité total_impact_eur = 0** hardcodé | Conformité | Le score dit 59/100 mais l'impact financier dit 0 € | P1 | S | KPI |
| C11 | **Command Palette** montre "Cockpit — Pilotage" pour 5 entrées en double | Search | Pollution des résultats de recherche | P2 | S | UX |
| C12 | **Segmentation "Tertiaire Privé 30%"** — questionnaire partiellement rempli | Segmentation | Page experte sans valeur en démo standard | P2 | XS | Démo |

---

## 4. Audit détaillé par zone

### 4.1 Cockpit

**Ce qui fonctionne :**
- Vue exécutive bien structurée : 3 alertes, score 55/100, économies potentielles 7 k€
- 4 blocs scoring (Pilotage/Patrimoine/Énergie/Achat) avec jauges
- Section "5 leviers activables" avec CTA "Créer une action"
- Bandeau "Prochaine échéance — Attestation d'affichage énergétique" — très crédible
- Activation des données 5/7 briques — bonne visibilité

**Ce qui est faible :**
- Score 55/100 en jaune — le cockpit semble "moyen" par défaut, pas rassurant
- Section "À surveiller" vide avec donut vide + "Tout va bien / Synchronisation de données" — contradictoire
- Le score "Achat" montre un badge mais le texte n'est pas lisible à cette taille
- Footer data activation montre "100% / 800 MWh/an / 1 site / 56%" — incohérent (5 sites seedés, affiche 1)

**Ce qui est trompeur :**
- readinessScore utilise un score actions binaire (55 ou 80, hardcodé dans constants.js)
- "100 %" couverture données affiché mais seulement pour 1 site

**Ce qu'un prospect remarquera immédiatement :**
- Le score 55/100 est le premier chiffre visible — un prospect demandera "pourquoi si bas ?"

---

### 4.2 Patrimoine

**Ce qui fonctionne :**
- 5 sites avec heatmap couleur (vert→rouge), risque global 266 k€
- Badges "DÉCRET TERTIAIRE" / "FACTURATION" sur les sites à risque
- Drawer site détaillé (résumé, anomalies, compteurs, actions)
- Profil énergie "Tertiaire Privé 30%"
- Score DPE par site visible

**Ce qui est faible :**
- Heatmap montre 5 sites mais "Ecole Jules Ferry Marseille" est isolée (la seule non-rouge)
- Tableau trié par risque mais pas de filtre par type

**Ce qui manque :**
- Pas de carte géographique visible (le composant SitesMap existe mais n'est pas affiché par défaut)

---

### 4.3 Consommation (Explorer + Portfolio + Import)

**Ce qui fonctionne :**
- Explorer avec filtres énergie (Elec/Gaz/PCI/RIU/PTO/Délégation), période, comparaison
- KPIs : 527 MWh, 84 148 EUR, 119.30 €/MWh, 27 tCO₂e, 240 kW, score 19/s
- Graphique barres bien lisible avec pattern mensuel
- Portfolio : vue tableur multi-sites avec % couverture
- Import wizard 7 étapes avec sélection site

**Ce qui est faible :**
- Explorer et page Consommations sont le même contenu (07 et 08 identiques au pixel)
- Score "19/s" — unité incompréhensible (devrait être "19 % solaire" ou "score 19")

**Ce qui est trompeur :**
- "4 037 relevés" affiché — le prospect ne sait pas si c'est beaucoup ou peu

---

### 4.4 Facturation / Bill Intelligence

**Ce qui fonctionne :**
- 36 factures, 748 871 €, 3 283 210 kWh — chiffres cohérents
- Shadow billing drawer détaillé : décomposition 5 composantes (Fourniture, Réseau, Taxes, TVA, Abonnement)
- Confiance "Élevé" / "Moyen" affiché par insight
- Timeline : couverture mensuelle avec barres, périodes manquantes identifiées
- CTA "Créer une action" sur chaque anomalie

**Ce qui est faible :**
- **52 anomalies pour 36 factures** — trop. "Écart shadow billing +156.9%" sur presque toute facture
- 20+ cards d'anomalies en scroll sans pagination — illisible
- Le premier insight prominent est +12 225 € d'écart — impressionnant mais trop systématique
- Labels "Ecart facture / consommation" + "Ecart lignes/total" + "RL mismatch" mélangés sans hiérarchie

**Ce qu'un prospect remarquera immédiatement :**
- "Toutes les factures ont une anomalie" → "Soit votre moteur est mal calibré, soit mes données sont fausses"

---

### 4.5 Achat Énergie

**Ce qui fonctionne :**
- Bandeau marché intelligent : "Le marché spot est à 75 EUR/MWh, 5% au-dessus de la moyenne 12 mois"
- Simulation complète : 1 739 006 kWh/an, profil 1.25, 4 scénarios
- Scoring risque 42/100, recommandation "Tarif Heures Solaires"
- Drawer offre détaillé avec avantages/inconvénients/points de vigilance
- CTA bottom : "Créer une action / Voir les actions / Exporter Note de Décision DAF"

**Ce qui est faible :**
- "Brique 3 — Post-ARENH v3.0" dans le sous-titre — jargon interne visible
- Label "Hypothèses" avec "Volume (MWh/an)" + "Puissance (kWh)" — pourquoi kWh pour puissance ?

**Ce qui est fort :**
- Meilleur module du produit. Parcours complet, data crédible, recommandation défendable.

---

### 4.6 Actions & Suivi

**Ce qui fonctionne :**
- 12 actions, 82 714 EUR estimés, avancement visuel (5 à planifier, 6 en cours, 1 terminée)
- Filtres par statut, type, priorité
- Tableau avec site, priorité, impact EUR, échéance, responsable

**Ce qui est faible :**
- Badge "7" sur Actions dans la sidebar — d'où vient ce 7 ? (12 actions en base)
- Les montants "437 EUR", "333 EUR" semblent aléatoires pour des actions d'économie d'énergie
- "Combattre la surconsommation détectée" — verbe "combattre" trop martial pour un energy manager

---

### 4.7 Conformité

**Ce qui fonctionne :**
- Score 59/100 avec frise réglementaire (BACS, Décret Tertiaire, Loi APER, CSRD)
- 3 non-conformités à traiter avec CTA "Voir le plan d'exécution"
- Onglets : Obligations / Données & Qualité / Plan d'exécution / Process & Rapports
- Chaque obligation listée avec sites, conformité %, échéance

**Ce qui est faible :**
- total_impact_eur = 0 hardcodé — le score dit 59 mais impact financier absent
- "1 obligation en retard — échéance dépassée" — quelle obligation ? Pas visible directement

**Ce qui est trompeur :**
- Score 59/100 calculé depuis `complianceScore.score ?? complianceScore.avg_score` — l'API retourne `avg_score`, le fallback `score` n'existe pas

---

### 4.8 Notifications

**Ce qui fonctionne :**
- 10 alertes bien typées (consommation, facture, conformité, contrat, BACS)
- Badges critiques/avertissement bien colorés
- Impact EUR par notification
- Dates récentes et réalistes

**Ce qui est faible :**
- Toutes les notifications datent de "2025-08" — devrait être 2026 (on est en mars 2026)
- Pas de marquage lu/non-lu visible dans le tableau

---

### 4.9 Admin (Users / Onboarding / Connectors / Activation / Status)

**Users :** Propre. 4 utilisateurs, 4 rôles distincts, scopes O:1. Crédible.

**Onboarding :** **CRITIQUE** — Progression 0/6, 0% — malgré données complètes. Race condition entre seed et API.

**Connectors :** 5 connecteurs mais 3 affichent "(stub)" dans leur description :
- meteofrance : "Meteo-France API (stub - cle requise)"
- enedis_opendata : "Enedis Open Data (stub)"
- enedis_dataconnect : "Enedis Data Connect OAuth (stub - cles requises)"

**Activation :** "5/5 briques actives" mais le tableau ne montre **1 seul site** (Siege HELIOS Paris). Les 4 autres manquent.

**Status :** Propre. Backend connecté, 7/7 endpoints OK, "PROMEOS v1.0" en footer.

---

### 4.10 Pages secondaires

**Diagnostic :** Page avec 50+ lignes de compteurs dupliqués (même site/type répété 4-6× pour des mois différents). Aucune pagination. Effet "dump de base de données".

**Usages Horaires :** Excellent. Score comportement 99, heatmap 7×24, talon 6.45 kW, facteur de charge 7.3.

**Segmentation :** Questionnaire 8 questions, "Tertiaire Privé 30%" — fonctionnel mais sans valeur en démo.

**Mémobox (KB) :** 0 items. "Explorez la base de connaissances" avec tags cliquables mais aucun contenu.

**Energy Copilot :** 0/0/- (à valider / propositions / économies). Page accessible, totalement vide.

---

### 4.11 Sidebar / Header / ScopeSwitcher

**Sidebar :** Contextuelle par module (Pilotage / Patrimoine / Énergie / Achat / Admin). Propre, pas surchargée. Badge "10" sur Performance.

**Header :** Breadcrumbs cohérents. Toggle Expert. Barre de recherche Ctrl+K.

**ScopeSwitcher :** Groupe HELIOS avec site sélectionnable. Fonctionne. Mais le site "Siege HELIOS Paris" est pré-sélectionné sur certaines pages même quand le contexte est org-level.

---

### 4.12 Command Palette (Ctrl+K)

**Ce qui fonctionne :** 5 entrées visibles (Cockpit, Actions & Suivi, Notifications, Sites & Bâtiments, Conformité OPERAT). Navigation rapide.

**Ce qui est faible :** Résultats limités aux pages visibles + hidden. Pas de recherche de sites, actions, factures.

---

## 5. Contradictions & pertes de confiance

| # | Contradiction | Impact |
|---|---------------|--------|
| 1 | **Onboarding 0/6** mais données complètes (5 sites, 36 factures, 12 actions) | Crédibilité |
| 2 | **Activation 1 site** mais patrimoine montre 5 sites | Cohérence |
| 3 | **Score conformité 59/100** mais impact financier = 0 € | KPI |
| 4 | **Score actions binaire** 55 ou 80, pas corrélé aux 12 actions réelles | KPI |
| 5 | **52 anomalies / 36 factures** — quasi toutes les factures sont "anomaliques" | Plausibilité |
| 6 | **Cockpit "1 site"** en footer mais 5 sites dans patrimoine | Scope |
| 7 | **Connecteurs "(stub)"** alors que la page laisse croire à des intégrations réelles | Démo |
| 8 | **Notifications de 2025-08** en mars 2026 — dates périmées | Crédibilité |
| 9 | **Badge "7"** sur Actions dans sidebar mais 12 actions en base | Data |
| 10 | **Energy Copilot visible dans nav** mais 0 contenu | Navigation |

---

## 6. Audit customer journey / workflow

### Où le parcours est bon
- **Cockpit → Patrimoine** : clic sur bloc "Patrimoine" ouvre la page avec contexte
- **Bill Intel → Drawer** : clic sur anomalie ouvre shadow billing décomposé
- **Achat → Simulation → Offres** : parcours complet de bout en bout
- **Conformité → Plan d'exécution** : logique obligation → action claire

### Où le parcours casse
- **Cockpit → "Tout va bien"** : le bloc "À surveiller" est vide avec un donut sans données — contradictoire avec le score 55/100
- **Cockpit footer → "1 site"** : le prospect pense qu'il n'y a qu'un seul site
- **Bill Intel scroll** : après 5 anomalies, le prospect perd le fil (pas de pagination, pas de regroupement)

### Où l'utilisateur hésite
- **Actions vs Anomalies** : deux concepts proches, accessible depuis des endroits différents
- **Explorer vs Consommations** : mêmes données, mêmes graphiques, deux entrées
- **Mémobox vs KB** : même page, accessible via sidebar ET via onglet conso

### Où PROMEOS ressemble à un outil et non à un cockpit
- **Diagnostic** : dump de compteurs sans synthèse
- **Import wizard 7 étapes** : bon pour un admin, intimidant pour un prospect
- **Segmentation questionnaire** : utile en fond, inutile en démo

---

## 7. Audit spécial chiffres / KPI / calcul

### KPI fiables
- **3 940 749 kWh** total consommation (portfolio) — cohérent avec le nombre de sites
- **748 871 € / 36 factures** — montant moyen ~20k€/facture, plausible pour 5 sites tertiaires
- **266 k€ risque global patrimoine** — cohérent avec le nombre de non-conformités
- **Heatmap usages** : score 99, talon 6.45 kW, pointe 88 kW — ratios réalistes

### KPI opaques
- **Score 55/100 cockpit** — composé de sous-scores avec poids arbitraires (30% data + 40% conformité + 30% actions)
- **42/100 risque achat** — algorithme de scoring non explicité dans l'UI
- **Score conformité 59/100** — `avg_score` mais aucune explication de la méthode

### KPI contradictoires
- **Conformité 59/100 + impact 0 €** — le score dit "à risque" mais l'impact dit "rien à faire"
- **Activation 5/5 briques + 1 site visible** — 5 briques actives mais un seul site dans le tableau

### Chiffres mal visibles
- **Score "19/s"** dans l'explorer conso — unité incompréhensible
- **"4 037 relevés"** dans la barre explorer — sans contexte (combien attendu ?)

### Calculs suspects
- **shadow_gap** sur quasi toutes les factures — seuil 20% mais les montants seedés dévient systématiquement >20%
- **readinessScore** = 0.3×data + 0.4×conformité + 0.3×(55|80) — le dernier terme est un placeholder

---

## 8. Audit spécial démo / quasi-production

### Ce qui fait encore POC
| Signal POC | Page | Impact |
|------------|------|--------|
| Onboarding 0/6 malgré seed | /onboarding | Rupture de confiance |
| "(stub)" dans 3 connecteurs | /connectors | Technique exposée |
| Activation 1 site / 5 | /activation | Données incomplètes |
| Energy Copilot 0/0/- | /energy-copilot | Page morte |
| Mémobox 0 items | /kb | Base vide |
| Diagnostic 50+ lignes sans pagination | /diagnostic-conso | Dump technique |
| Notifications datées août 2025 | /notifications | Dates périmées |
| "Brique 3 — Post-ARENH v3.0" | /assistant-achat | Jargon interne |

### Ce qui fait produit mature
| Signal mature | Page |
|---------------|------|
| Shadow billing décomposé avec confiance | /bill-intel |
| 4 scénarios achat avec scoring et reco | /achat-energie |
| Heatmap usages 7×24 avec profil | /usages-horaires |
| Status page 7/7 OK + version | /status |
| 4 rôles utilisateurs distincts | /admin/users |
| Patrimoine heatmap + drawer site | /patrimoine |
| Conformité multi-framework + frise | /conformite |

---

## 9. Recommandations classées

### P0 — Corriger immédiatement (avant toute démo)

| # | Action | Effort |
|---|--------|--------|
| P0-1 | **Fixer onboarding** : détecter seed existant et marquer 6/6 automatiquement | S |
| P0-2 | **Supprimer "(stub)"** des descriptions connecteurs visibles dans l'UI | XS |
| P0-3 | **Activation** : afficher les 5 sites, pas seulement le site sélectionné | S |
| P0-4 | **Réduire anomalies billing** : augmenter seuil shadow_gap ou varier les montants seedés | M |
| P0-5 | **Masquer Energy Copilot** de la navigation (page vide) | XS |

### P1 — Corriger vite (semaine prochaine)

| # | Action | Effort |
|---|--------|--------|
| P1-1 | **Diagnostic** : paginer (20 lignes max) + dédupliquer compteurs | S |
| P1-2 | **Cockpit** : remplacer score actions binaire par calcul réel | M |
| P1-3 | **Conformité** : calculer total_impact_eur réel (pas 0) | S |
| P1-4 | **Notifications** : mettre à jour les dates seed vers 2026 | XS |
| P1-5 | **Mémobox** : seeder 5-10 règles de base (BACS, Décret Tertiaire, ARENH, CEE, CSPE) | S |
| P1-6 | **Bill Intel** : ajouter pagination (10 anomalies/page) + filtre par sévérité | M |
| P1-7 | **Renouvellements** : seeder contrats pour les 5 sites (pas seulement Siege Paris) | S |
| P1-8 | **Achat** : retirer "Brique 3 — Post-ARENH v3.0" du sous-titre | XS |

### P2 — Corriger ensuite

| # | Action | Effort |
|---|--------|--------|
| P2-1 | **Score "19/s"** → remplacer par "19 % solaire" ou supprimer | XS |
| P2-2 | **Cockpit "À surveiller"** : afficher données réelles ou masquer le donut vide | S |
| P2-3 | **Cockpit footer** : afficher "5 sites" au lieu de "1 site" | XS |
| P2-4 | **Command Palette** : ajouter recherche par site/action/facture | M |
| P2-5 | **Explorer/Consommations doublon** : fusionner ou différencier clairement | S |

### Surveiller seulement

| # | Item |
|---|------|
| S1 | Badge "7" vs 12 actions — vérifier la logique du badge (probablement filtré par statut) |
| S2 | Segmentation questionnaire — ne pas montrer en démo standard |
| S3 | Compliance API `avg_score` vs `score` — fonctionne via fallback mais fragile |

---

## 10. Plan priorisé

| Ordre | Action | Impact | Effort | Pourquoi maintenant |
|-------|--------|--------|--------|---------------------|
| 1 | Masquer Energy Copilot de la nav | Haut | XS | Page morte = signal POC |
| 2 | Supprimer "(stub)" des connecteurs | Haut | XS | 3 mots à changer |
| 3 | Retirer "Brique 3 — Post-ARENH v3.0" | Moyen | XS | Jargon visible |
| 4 | Fixer onboarding 0/6 → 6/6 | Haut | S | Premier signal de crédibilité |
| 5 | Activation : afficher 5 sites | Haut | S | Cohérence données |
| 6 | Cockpit footer "1 site" → "5 sites" | Moyen | XS | Cohérence |
| 7 | Notifications dates 2025→2026 | Moyen | XS | Crédibilité temporelle |
| 8 | Réduire anomalies billing (seuils seed) | Haut | M | 52 anomalies = non crédible |
| 9 | Paginer diagnostic (20 max) | Moyen | S | Lisibilité |
| 10 | Score actions réel (pas binaire) | Moyen | M | KPI défendable |
| 11 | Conformité total_impact_eur réel | Moyen | S | Cohérence score/impact |
| 12 | Mémobox : seeder 5 règles | Moyen | S | Page non-vide |
| 13 | Bill Intel : pagination anomalies | Moyen | M | Lisibilité |
| 14 | Renouvellements : contrats 5 sites | Moyen | S | Crédibilité module achat |

---

## 11. Verdict final

### PROMEOS est-il réellement crédible aujourd'hui ?
**Oui, pour une démo guidée.** Le parcours Cockpit → Patrimoine → Bill Intel → Achat est solide. Le module Achat est impressionnant. Le shadow billing est riche. Mais une exploration libre révèle trop de pages vides/cassées.

### Qu'est-ce qui empêche encore un effet "top world" ?
1. **L'inconsistance des données seed** — onboarding 0/6, activation 1 site, 52 anomalies, dates 2025
2. **Les pages mortes** — Energy Copilot, Mémobox, Diagnostic en dump
3. **Les KPI placeholder** — score actions binaire, impact conformité = 0

### Qu'est-ce qui doit être corrigé AVANT toute nouvelle feature ?
- Les 5 items P0 (onboarding, stub, activation, anomalies, copilot)
- Le score actions binaire (P1-2)
- La pagination Bill Intel et Diagnostic (P1-1, P1-6)

### Qu'est-ce qui doit être gelé car déjà assez bon ?
- Module Achat (simulation, scoring, offres)
- Shadow billing V2 (décomposition, explainability, confiance)
- Patrimoine (heatmap, drawer, risque global)
- Usages Horaires (heatmap 7×24, profil comportemental)
- Navigation contextuelle (sidebar, breadcrumbs, scope switcher)
- Admin Users (4 rôles, propre)
- Status page (7/7 OK, v1.0)

### Si tu devais montrer PROMEOS demain à un prospect exigeant, qu'est-ce qui te ferait peur ?
1. Le prospect clique sur "Démarrage" et voit 0/6 — **game over**
2. Le prospect ouvre les connecteurs et lit "stub" — confiance perdue
3. Le prospect scroll Bill Intel et voit 52 anomalies identiques — "votre moteur est cassé"
4. Le prospect ouvre Energy Copilot — page vide, gênant
5. Le prospect demande "combien d'économies ?" et le cockpit dit "7 k€" mais conformité dit "0 €" — contradiction

**Corrige les 5 P0 (< 1 journée de travail), et le score passe à 80+.** Le produit a la profondeur. Il lui manque la finition de surface.

---

*Audit généré le 10/03/2026 — PROMEOS v1.0 — 27 pages + 8 interactions analysées*
