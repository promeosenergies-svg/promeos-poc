# AUDIT TOTAL PROMEOS — V4 (2026-03-11)

**Méthode** : Playwright headless 27 pages + 3 agents code parallèles (routing, KPI, wording) + vérification API live.

---

# 1. Executive Summary

| Critère | Valeur |
|---------|--------|
| **Note globale** | **71/100** |
| **Verdict** | Produit impressionnant en richesse fonctionnelle, mais des failles de crédibilité visibles empêchent une démo sans risque |
| **Maturité réelle** | Beta avancée — pas encore production-ready pour un prospect exigeant |
| **Potentiel après correction** | 88/100 — le delta est faible en effort, fort en impact |

### 5 risques les plus graves

| # | Risque | Impact |
|---|--------|--------|
| 1 | **Onboarding affiche 0/6** malgré org + 5 sites + compteurs + factures + users + actions existants | Première impression catastrophique en démo — le produit ne "sait pas" ce qu'il contient |
| 2 | **Connecteurs affichent "(stub)"** dans l'UI — "Enedis Open Data (stub)", "Meteo-France API (stub - cle requise)" | Trahit un POC, pas un produit. Un prospect qui voit "stub" part |
| 3 | **52 anomalies pour 36 factures** — ratio >1.4 anomalie/facture sur un portefeuille sain seed | Détruit la crédibilité du moteur billing — un DG conclut "votre IA alerte sur tout" |
| 4 | **Diagnostic conso** : 40+ lignes sans pagination, illisible | Page inutilisable en démo — scroll infini, données non hiérarchisées |
| 5 | **Renouvellements** : 2 contrats sur 1 seul site / 5 | Module Achat semble vide pour 80% du patrimoine |

### 5 forces réelles

| # | Force |
|---|-------|
| 1 | **Cockpit exécutif** : dense, structuré, 4 KPI + briefing + watchlist + sparklines — niveau produit mature |
| 2 | **Achat Énergie / Scénarios** : 4 stratégies comparées, scoring, recommandation — valeur business immédiate |
| 3 | **Usages Horaires** : heatmap 7×24, score comportement, talon/pointe/dérive — niveau expert world-class |
| 4 | **Conformité** : 3 frameworks (DT, BACS, APER), score pondéré, frise réglementaire, plan d'action |
| 5 | **Architecture navigation** : sidebar contextuelle, 5 modules colorés, breadcrumb, command palette Ctrl+K |

---

# 2. Note détaillée par dimension

| Dimension | Note /10 | Commentaire sévère |
|-----------|----------|-------------------|
| **UX** | 7.5 | Parcours globalement fluides, bon drill-down site→page, mais certaines pages sont des murs de données sans hiérarchie (Diagnostic, Bill Intel) |
| **UI** | 8.0 | Design system cohérent, cards/tables propres, bonne typographie. Quelques incohérences de densité entre pages |
| **Navigation** | 8.5 | Sidebar contextuelle + rail + breadcrumb + Ctrl+K excellent. Aucune route morte. 27 redirects d'alias bien gérés |
| **Scope / gouvernance** | 7.0 | ScopeSwitcher fonctionnel mais pas toujours rappelé. Activation fonctionne bien org-level (fix P0-3 OK). Admin Users propre |
| **KPI / calcul** | 6.0 | Score Actions binaire (55 ou 80), prix fallback 0.068€/kWh obsolète (2021), risque financier flat-rate 7500€/obligation, compliance surface-weighted mais non expliqué |
| **Facturation / achat** | 6.5 | Shadow billing V2 solide mais 52 anomalies sur 36 factures détruit la crédibilité. Achat excellent mais seulement 1 site couvert en contrats |
| **Workflow / actionability** | 7.5 | Constat→action bien connecté via drawers. Création d'action depuis toutes les pages. Timeline d'action existante |
| **Demo credibility** | 5.5 | Onboarding 0/6, "(stub)" visible, "Brique 3 — Post-ARENH v3.0.0", "Mode demo" checkbox, KB vide 0 items, accents manquants |
| **Architecture visible** | 7.5 | Pas de localhost visible, pas de stack trace, API abstraite. Mais `source="demo_seed"` dans les données, labels UTF-8 cassés dans onboarding API |
| **Wording / microcopy** | 6.5 | Globalement bon FR mais 15+ occurrences d'accents manquants ("Donnees", "meteorologiques", "Derniere", "periode"), labels techniques visibles |
| **Responsive / densité** | 7.0 | Bon sur desktop 1920px. Diagnostic/Bill Intel trop denses. Pas de responsive mobile testé |
| **Product story** | 8.0 | Narrative cohérente : patrimoine→conformité→conso→billing→achat→actions. Storytelling solide si les failles de crédibilité sont corrigées |

---

# 3. Top problèmes critiques

| ID | Problème | Zone | Pourquoi c'est grave | Priorité | Effort | Type |
|----|----------|------|---------------------|----------|--------|------|
| P0-1 | **Onboarding 0/6 malgré données existantes** — l'auto-detect ne fonctionne pas sur le serveur live | Onboarding | Un prospect voit "vous n'avez rien configuré" alors que tout est seedé — incohérence fatale | P0 | S | Technique |
| P0-2 | **"(stub)" visible dans Connecteurs** — descriptions anciennes servies par le backend | Connectors | Le mot "stub" = POC. Un investisseur qui voit ça doute de tout | P0 | XS | Wording |
| P0-3 | **52 anomalies / 36 factures = ratio 1.4** — le seed génère trop d'alertes shadow billing | Bill Intel | Le moteur d'anomalies perd toute crédibilité. "Votre IA alerte sur tout" | P0 | M | Data/Calcul |
| P0-4 | **"Brique 3 — Post-ARENH v3.0.0"** visible en titre Assistant Achat | Achat | Version interne + nom technique visible — pas de sens pour un utilisateur | P0 | XS | Wording |
| P0-5 | **"Mode demo" checkbox** visible dans Assistant Achat | Achat | Trahit un environnement de test, pas un produit | P0 | XS | Démo |
| P1-1 | **Diagnostic conso sans pagination** — 40+ lignes en scroll infini | Diagnostic | Page inutilisable, données non hiérarchisées | P1 | S | UX |
| P1-2 | **Renouvellements : 2 contrats / 1 site** — 4 sites sans contrat | Achat | Module Achat semble vide pour 80% du patrimoine | P1 | M | Data |
| P1-3 | **KB/Mémobox vide : 0 items** — pas de seed | KB | Page accessible mais totalement vide — aucune valeur démo | P1 | M | Data |
| P1-4 | **Accents manquants (15+ occurrences)** — "Donnees", "meteorologiques", "electrique", "Derniere" | Multi-pages | Fait amateur pour un produit B2B France | P1 | S | Wording |
| P1-5 | **Score Actions binaire** — 55 ou 80, pas de valeur continue | Cockpit KPI | 1 site non-conforme sur 100 = même score que 50/100. Cliff effect non crédible | P1 | S | Calcul |
| P1-6 | **Notifications dates passées** — alertes datées mais pas refresh depuis le seed | Notifications | Dates figées donnent l'impression d'un système inactif | P1 | S | Data |
| P1-7 | **Prix fallback 0.068€/kWh** dans shadow billing | Billing | Tarif 2021, complètement décalé vs 2025-2026 (≈0.12-0.18€). Fausse tout calcul sans contrat | P1 | XS | Calcul |
| P1-8 | **Risque financier flat-rate 7500€/obligation** | Conformité | Un magasin 200m² = même pénalité qu'un siège 10000m². Non crédible pour un expert | P1 | M | Calcul |
| P2-1 | **Bill Intel : pas de pagination factures** — liste longue en bas de page | Bill Intel | Scroll nécessaire, pas de tri/filtre avancé | P2 | S | UX |
| P2-2 | **Portfolio Conso : tableau sans export visible** | Consommations | Le bouton Export est en haut, pas évident | P2 | XS | UX |
| P2-3 | **Performance page** : badges "Non détecté" peu explicites | Monitoring | "Non détecté" pour gaspillage = ambigu (pas de gaspillage ou pas de données?) | P2 | XS | Wording |
| P2-4 | **Segmentation "30%"** — profil incomplet visible | Segmentation | Montre un questionnaire partiellement rempli — impression d'abandon | P2 | S | Démo |

---

# 4. Audit détaillé par zone

## 4.1 Cockpit (Vue Exécutive)

**Ce qui fonctionne :**
- 4 KPI en bande (Conformité 59/100, Risque 23 k€, Couverture 78%, Maturité 100%) — lecture immédiate
- Briefing "KPIs executifs" en popover avec synthèse textuelle
- Watchlist avec priorités recommandées et CTA "Créer une action"
- Sparklines par module (Pilotage, Patrimoine, Énergie, Achat) — vision radar
- Section "Activation des données" avec barres 100% / 5 sites / 1 450 MWh/an
- Alerte conformité en rouge en bas "2 sites non conformes ou à risque"

**Ce qui est faible :**
- Le score Maturité "100%" est une valeur plafond qui ne progresse pas — perd l'intérêt
- Couverture données "78%" alors qu'Activation montre "100% des sites" — contradiction apparente (expliquée par 78% = détail par champ, 100% = sites avec conso > 0, mais un DG ne comprend pas)
- 4 briques activées puis en bas "5/5 briques actives" — incohérence numérique (4 vs 5)
- Section "À surveiller" montre "Décret Tertiaire" avec un texte mais pas de chiffre — faible

**Ce qui est trompeur :**
- Le score Conformité 59/100 est pondéré par surface mais ce n'est dit nulle part — un utilisateur croit que c'est une moyenne simple
- Risque 23 k€ = 7500€ × nombre d'obligations. Pas calibré à la réalité du portefeuille

## 4.2 Patrimoine (Sites & Bâtiments)

**Ce qui fonctionne :**
- Résumé "5 sites · 17 741 m² · 21.58 M risque" — clair
- Heatmap visuelle rouge/jaune/vert par site
- Profil portefeuille "Tertiaire Privé 89%"
- Filtres par usage + tags
- Table triable avec surface, conformité, risque

**Ce qui est faible :**
- "Risque global 209 k€" en badge — gros chiffre mais sans contexte (209k€ sur quoi? Pourquoi?)
- "100% " avec un badge vert mais le sens n'est pas clair (100% de quoi?)

**Ce qui manque :**
- Pas de carte géographique malgré les villes connues (Paris, Lyon, Toulouse, Nice, Marseille)

## 4.3 Conformité réglementaire

**Ce qui fonctionne :**
- Score 59/100 avec breakdown DT/BACS/APER — transparent
- Frise réglementaire chronologique
- 3 obligations détaillées avec boutons "Créer action" / "Dossier"
- Tabs bien structurés : Obligations, Données & Qualité, Plan d'exécution, Preuves

**Ce qui est faible :**
- "3 non-conformités à traiter" en rouge = urgent, mais la page ne propose pas de CTA global "Traiter tout"
- Le plan d'exécution est un concept mais pas implémenté dans le tab
- Badge "1 obligation en retard — échéance dépassée" en rouge est fort mais le détail est caché

## 4.4 Conformité Tertiaire / OPERAT

**Ce qui fonctionne :**
- Vue claire : 6 sites, 3 EFA déclarables, 3 prochaines étapes, 0 anomalies
- Filtres par statut (Enquête produite, À traiter, Site EFA)
- Bouton "Créer EFA" / "Exporter OPERAT"

**Ce qui est faible :**
- Liste longue d'EFAs sans hiérarchie ni groupement
- Certaines EFA montrent "Tour Montparnasse Est — Bureau Regional Lyon" avec des noms composés longs

## 4.5 Consommations (Explorer)

**Ce qui fonctionne :**
- KPIs bien visibles : 521 MWh, 83 164 EUR, 119.60 €/MWh, 27 t CO₂e, 240 kW, 19%
- Graphe barres mensuel propre et lisible
- Filtres énergie (Electricité/Gaz) + période + granularité
- "Comparer à la courbe moyenne des sites similaires" en option

**Ce qui est faible :**
- Le scope est figé sur "Siege HELIOS Paris" — le scope switcher a réduit à 1 site
- Pas de vue comparative multi-sites dans cet onglet (il faut aller sur Portefeuille)

## 4.6 Consommations (Portefeuille)

**Ce qui fonctionne :**
- Totaux clairs : 3 909 900 kWh, 265 873 EUR, 222 473 kg CO₂, 5/5 sites
- Couverture 98% — badge rassurant
- Table par site avec toutes les métriques

**Ce qui est faible :**
- "Impact financier estimé / Données dérivées / Piste de puissance" en haut — concepts non expliqués

## 4.7 Diagnostic consommation

**Ce qui est cassé :**
- **40+ lignes sans pagination** — la page est un mur de texte
- Tous les rows ont des couleurs de badges similaires — pas de hiérarchie
- Les descriptions sont des phrases longues tronquées — illisible en table
- Pas de filtre par sévérité ou type d'anomalie
- Mélange de sites et compteurs dans la même table

**Verdict :** Page inutilisable en l'état pour une démo.

## 4.8 Monitoring / Performance

**Ce qui fonctionne :**
- Vue par site avec KPIs : 4 155 EUR/an, gaspillage, 11.9 t/an, 72% solaire
- Plan d'action avec recommandation et estimation
- Section technique pour experts

**Ce qui est faible :**
- "Non détecté" pour gaspillage — ambigu (pas de gaspillage? pas de données?)
- Un seul site visible, pas de vue portefeuille

## 4.9 Usages Horaires

**Ce qui fonctionne (excellent) :**
- Heatmap 7×24 : couleurs Normal/À surveiller/Anormal — immédiatement lisible
- Score comportement : 99 "Bon" — simple et clair
- Talon 6.45 kW, Dérive 0%
- Avertissement "Weekend actif — 34% de consommation samedi-dimanche"
- Profil journalier en graphe 0-24h
- KPIs Talon (Q10), Pointe (P90), Facteur de charge

**Verdict :** Page world-class. Ne rien toucher.

## 4.10 Facturation / Bill Intel

**Ce qui fonctionne :**
- KPIs : 36 factures, 748 871 €, 3 283 210 kWh, 52 anomalies, 90 856 € pertes
- Shadow billing expliqué "Comment ça marche ?"
- Anomalies listées avec sévérité, montant, type, CTA "Comprendre l'écart"

**Ce qui est cassé :**
- **52 anomalies pour 36 factures = ratio 1.44** — non crédible. Un portefeuille seedé "sain" ne devrait pas avoir plus d'anomalies que de factures. Cela signifie que plusieurs règles tirent sur chaque facture (shadow_gap + unit_price + volume_spike). Le seed doit être calibré.
- **90 856 € d'économies potentielles** — chiffre énorme pour 748k€ de factures (12%). Crédible si le portefeuille a vraiment des anomalies, mais contradictoire avec un seed "bien configuré"
- Liste d'anomalies sans pagination (scroll long)

**Ce qui est faible :**
- Beaucoup d'anomalies "Écart facture / consommation" avec des badges similaires — manque de variété visuelle
- Table factures en bas de page coupée — nécessite scroll
- Badge "10" sur Performance dans la sidebar — 10 quoi? Pas contextuel

## 4.11 Billing Timeline

**Ce qui fonctionne :**
- Vue chronologique mensuelle propre
- Comparaison barres mensuel 2025-2026
- Périodes manquantes identifiées avec badges et CTA "CSV" / "PDF"
- Timeline complète avec statuts

**Ce qui est faible :**
- 10 "périodes manquantes ou incomplètes" — beaucoup pour 5 sites. Normal ? Ou seed incomplet ?

## 4.12 Achat Énergie (Stratégies)

**Ce qui fonctionne (excellent) :**
- Alerte marché "Le marché spot est à 75 EUR/MWh" — contexte immédiat
- Sélection site + volume + prix de référence
- Hypothèses configurables (indexation, horizon, énergie)
- Scénarios 2026-2030 : 4 stratégies comparées (Prix Fixe, Indexé, Tarif Heures Solaires, Spot)
- Scoring 42/100, recommandation claire
- Chaque stratégie : prix, évolution vs actuel, points clés

**Ce qui est faible :**
- Seulement "Siege HELIOS Paris" en scope — les 4 autres sites n'ont pas de contrat
- "Enveloppe Budget: 50%" slider — qu'est-ce que ça veut dire?

## 4.13 Assistant Achat

**Ce qui est cassé :**
- **"Brique 3 — Post-ARENH v3.0.0"** en sous-titre — label interne + version technique visibles à l'utilisateur
- **"Mode demo"** checkbox en haut à droite avec "Tout selectionner" — trahit un mode test

**Ce qui fonctionne :**
- Wizard 8 étapes structuré (Portefeuille → Conso → Persona → Horizon → Offres → Résultats → Scoring → Décision)
- 5 sites chargés depuis le patrimoine
- Cartes de site propres avec ville + MWh/an + m²

## 4.14 Renouvellements

**Ce qui fonctionne :**
- Filtres temporels (30j, 60j, 90j, 180j, 1 an)
- Badges couleur : 1 bientôt (89j orange), 1 actif (295j vert)
- Profil Tertiaire Privé 30% avec CTA "Affiner"

**Ce qui est faible :**
- **2 contrats sur 1 seul site (Siege HELIOS Paris)** — les 4 autres sites n'ont aucun contrat
- La page est quasi-vide avec 2 lignes — impression de module non déployé
- "Profil a 30% — repondez a 2 questions" — accents manquants ("à", "répondez")

## 4.15 Admin Users

**Ce qui fonctionne :**
- 4 utilisateurs avec rôles colorés (DG/Owner, Energy Manager, Auditeur, Resp. Site)
- KPI : 1 actif ce mois, 3 sans connexion (rouge)
- Scopes "O:1" visibles

**Ce qui est faible :**
- "3 Sans connexion" en rouge — alarme forte pour un environnement de démo où les users n'ont jamais eu besoin de se connecter
- "Dernière connexion: Jamais" pour 3 users — normal en seed mais alarme visuelle

## 4.16 Onboarding

**Ce qui est cassé :**
- **Progression 0/6 = 0%** malgré org existante, 5 sites, compteurs, factures, 4 users, actions
- L'auto-detect devrait cocher toutes les 6 étapes. Le fix P0-1 est dans le code source mais le serveur live ne l'exécute pas (serveur non redémarré ou bug dans la chaîne Portefeuille→EntiteJuridique→Organisation)
- Impression catastrophique : "le produit ne sait pas ce qu'il contient"

## 4.17 Connectors

**Ce qui est cassé :**
- **"Enedis Open Data (stub)"** — le mot "stub" visible
- **"Enedis Data Connect OAuth (stub - cles requises)"** — idem
- **"Meteo-France API (stub - cle requise)"** — idem
- Le code source est fixé (P0-2) mais le serveur live sert les anciennes descriptions

**Ce qui fonctionne :**
- Layout propre en cards, boutons Test/Sync, badges Public/Auth requise
- Section "À propos des Connecteurs" avec descriptions

**Ce qui est faible :**
- Accents manquants dans "À propos" : "electrique", "Donnees", "meteorologiques"

## 4.18 Activation des données

**Ce qui fonctionne (P0-3 fixé) :**
- 5/5 briques actives — affiche bien tous les 5 sites (fix orgSites OK)
- Matrice site × dimension avec checkmarks
- Filtres par dimension avec compteur de sites manquants
- "Usine HELIOS Toulouse" : Conformité manquante (cercle gris) — correct

**Ce qui est faible :**
- "Conformite reglementaire" sans accent sur le "é"
- "Donnees de consommation" sans accent
- "Contrats energie" sans accent

## 4.19 Status / Système

**Ce qui fonctionne :**
- Backend connecté, 6/6 checks OK, version v1.0
- Endpoints vérifiés individuellement (health, Sites, Cockpit, KB, Monitoring, Bill Rules, OpenAPI)

**Ce qui est faible :**
- "Derniere verification" — accent manquant sur "Dernière" et "vérification"
- "Backend connecte" — accent manquant sur "connecté"

## 4.20 KB / Mémobox

**Ce qui est cassé :**
- **0 items — page totalement vide**
- Warning "KB locale chargée — Le service Mémobox n'est pas disponible"
- Tous les filtres (Réglementaire, Usages, ACC, Facturation, Flex) à (0)
- Pas de seed → aucune valeur en démo

## 4.21 Segmentation B2B

**Ce qui fonctionne :**
- Questionnaire structuré avec 8 questions
- Profil "Tertiaire Privé" identifié à 30%

**Ce qui est faible :**
- 30% = profil incomplet — en démo, ça montre un formulaire abandonné
- Questions 6-8 sont des boutons radio non sélectionnés — l'utilisateur voit "vous n'avez pas fini"

## 4.22 Sidebar / Header / Scope

**Ce qui fonctionne :**
- Rail 5 modules colorés (Pilotage bleu, Patrimoine vert, Énergie indigo, Achat ambre, Admin gris)
- Panel contextuel qui change par module
- Breadcrumb dynamique "PROMEOS > Module > Page"
- ScopeSwitcher "Groupe HELIOS · Siege HELIOS Paris" avec X pour clear
- Badge "7" sur Actions & Suivi, "10" sur Performance
- Recherche Ctrl+K accessible

**Ce qui est faible :**
- Le badge "10" sur Performance — c'est quoi ces 10? Pas contextuel
- En mode admin, la sidebar s'allège beaucoup (4 items) — contraste fort avec les 12+ items du mode expert

## 4.23 Notifications

**Ce qui fonctionne :**
- 3 critiques, 5 importantes, 2 avertissements — hiérarchie claire
- Filtres par statut (Toutes, Nouvelles, Lues, Ignorées)
- Dates et montants d'impact estimé
- Descriptions utiles : "Consommation hors horaire abusive", "Taxon inapproprié"

**Ce qui est faible :**
- Dates visibles (2025-08, 2025-09) — passées de 6+ mois, donne l'impression d'alertes non traitées
- "Toutes courtes" en filtre — pas clair

---

# 5. Contradictions & pertes de confiance

| # | Contradiction | Impact |
|---|--------------|--------|
| 1 | **Cockpit "4 briques activées"** vs Activation **"5/5 briques actives"** | Un DG qui navigue entre les deux pages voit 4 et 5 — quelle est la vérité ? |
| 2 | **Cockpit "Couverture 78%"** vs Activation **"100% des sites"** | 78% de quoi vs 100% de quoi ? Pas la même métrique mais présenté au même niveau |
| 3 | **Onboarding 0/6** vs Activation **5/5 actives** | Deux pages qui se contredisent sur l'état de configuration de la plateforme |
| 4 | **52 anomalies** sur **36 factures** | Plus d'alertes que de factures → le moteur détecte trop |
| 5 | **Score conformité 59/100** (cockpit) mais **3/5 sites conformes** (patrimoine) | 59% ≠ 60% — la pondération par surface n'est pas expliquée |
| 6 | **"Brique 3"** comme titre d'une page utilisateur | Label interne non traduit en label produit |
| 7 | **"(stub)"** dans descriptions connecteurs | Vocabulaire développeur dans l'UI |
| 8 | **"Mode demo" checkbox** visible | Contrôle interne exposé |
| 9 | **Risque "209 k€"** (patrimoine) vs **"23 k€"** (cockpit) | Deux chiffres de risque totalement différents sur deux pages |
| 10 | **Notifications datées 2025** | En mars 2026, des alertes de 6+ mois non traitées = système inactif |

---

# 6. Audit customer journey / workflow

## Scénario 1 — Prospect / démo commerciale

| Étape | Verdict |
|-------|---------|
| Arrive sur Cockpit | **BON** — 4 KPI lisibles, briefing clair, watchlist actionnable |
| Explore Patrimoine | **BON** — 5 sites, heatmap, profil portefeuille |
| Regarde Facturation | **MOYEN** — chiffres impressionnants mais 52 anomalies sur 36 factures est suspect |
| Regarde Achat | **BON** — scénarios convaincants, recommandation claire |
| Regarde Actions | **BON** — table propre, statuts visibles, CTA "Créer une action" |
| Regarde Onboarding | **CASSÉ** — 0/6 malgré données. Perte de confiance immédiate |
| Regarde Connecteurs | **CASSÉ** — "(stub)" visible. Le prospect se demande si c'est un vrai produit |
| **Verdict** | Le cockpit et l'achat sont vendeurs. L'onboarding et les connecteurs cassent tout |

## Scénario 2 — DG multi-sites

| Étape | Verdict |
|-------|---------|
| Change de portefeuille | Le ScopeSwitcher fonctionne mais il n'y a qu'un seul portefeuille dans le seed |
| Regarde cockpit + patrimoine | BON — vision claire |
| Cherche une recommandation | BON — watchlist du cockpit propose 3 actions prioritaires |
| Comprend où agir | BON — flèche vers "Créer une action" partout |
| Comprend combien ça vaut | MOYEN — le risque financier est flat-rate, pas crédible en valeur absolue |

## Scénario 3 — Energy manager

| Étape | Verdict |
|-------|---------|
| Cherche un site précis | BON — ScopeSwitcher + recherche + navigation site360 |
| Consulte KPI/anomalies | BON — explorer + monitoring + usages horaires |
| Crée une action | BON — drawer de création depuis n'importe quelle anomalie |
| Vérifie son périmètre | MOYEN — scope rappelé dans le header mais pas toujours clair dans les drawers |

## Scénario 4 — Expert

| Étape | Verdict |
|-------|---------|
| Passe en mode expert | Toggle visible dans le header |
| Pages avancées | Diagnostic inutilisable (pagination), Usages Horaires excellent |
| Command palette | BON — Ctrl+K fonctionne, 14 actions rapides, 10 raccourcis |
| Exploitabilité | MOYEN — certaines pages sont des murs de données |

## Scénario 5 — Admin

| Étape | Verdict |
|-------|---------|
| Admin Users | BON — 4 rôles, scopes, statuts |
| Permissions visibles | MOYEN — "O:1" comme scope n'est pas parlant pour un admin |
| Plateforme gouvernée | MOYEN — pas de journal d'audit visible dans la nav principale |

---

# 7. Audit spécial chiffres / KPI / calcul

## KPI fiables
- **Consommation kWh** : basée sur données réelles (metered/billed/estimated), confiance indiquée
- **Nombre de sites** : 5/5 cohérent partout (après fix P0-3)
- **Score conformité 59/100** : formule documentée (DT 45% + BACS 30% + APER 25%)
- **Usages horaires** : Talon/Pointe/Facteur de charge calculés correctement

## KPI opaques
- **Maturité plateforme** : formule cachée (data 30% + conformité 40% + actions 30%), actions = binaire
- **Risque financier** : flat-rate 7500€ × obligations, pas calibré à la taille du site
- **Score Actions** : 55 ou 80, jamais entre — cliff effect

## KPI contradictoires
- **"4 briques" vs "5/5 briques"** — deux pages, deux chiffres
- **"78% couverture" vs "100% des sites"** — deux métriques différentes présentées de manière similaire
- **"209 k€ risque" vs "23 k€ risque"** — patrimoine vs cockpit, échelles différentes

## Chiffres mal visibles
- **Shadow billing "expected"** : le montant attendu n'est visible qu'après clic "Comprendre l'écart"
- **Impact EUR des actions** : "62 714 EUR" en haut d'Actions mais pas corrélé aux actions individuelles

## Chiffres manquant de contexte
- **52 anomalies** : pas de ratio /facture visible. L'utilisateur ne sait pas si 52 c'est beaucoup ou normal
- **90 856 € économies** : pas de % du total facturé pour contextualiser
- **Score 42/100** dans Achat : sur quels critères ? Pas détaillé sans clic

## Calculs suspects
- **Prix fallback 0.068€/kWh** : obsolète (prix 2021), devrait être ≥0.12 en 2025-2026
- **Risque 7500€ par obligation** : identique quelle que soit la surface ou le type de bâtiment
- **Ratio anomalies/factures = 1.44** : le moteur de règles tire trop (plusieurs règles par facture)

---

# 8. Audit spécial démo / quasi-production

## Ce qui fait encore POC

| Signal POC | Lieu | Sévérité |
|-----------|------|----------|
| "(stub)" dans les connecteurs | Connectors page | **Critique** |
| "Brique 3 — Post-ARENH v3.0.0" | Assistant Achat | **Critique** |
| "Mode demo" checkbox | Assistant Achat | **Critique** |
| Onboarding 0/6 | Onboarding page | **Critique** |
| KB 0 items + warning "service non disponible" | Mémobox | **Élevé** |
| 52 anomalies / 36 factures | Bill Intel | **Élevé** |
| Accents manquants × 15 | Multi-pages | **Moyen** |
| Notifications datées 2025 | Notifications | **Moyen** |
| `source="demo_seed"` dans les données | Backend data | **Faible** (non visible UI) |
| `engine_version="demo_seed_v87"` | Backend data | **Faible** (non visible UI) |

## Ce qui fait produit mature

| Signal Mature | Lieu |
|--------------|------|
| Sidebar contextuelle 5 modules avec couleurs | Global |
| Cockpit executive avec briefing et watchlist | Cockpit |
| Heatmap 7×24 usages horaires | Usages |
| 4 scénarios d'achat avec scoring | Achat |
| Shadow billing V2 avec 5 composantes | Bill Intel |
| Frise réglementaire conformité | Conformité |
| Timeline facturation avec détection manques | Billing Timeline |
| Command palette Ctrl+K | Global |
| Admin Users avec rôles et scopes | Admin |
| 27 redirects d'alias proprement gérés | Routing |

## Ce qui bloque une vraie démo client
1. L'onboarding qui dit "vous n'avez rien fait" alors que tout est configuré
2. Le mot "stub" dans les connecteurs
3. Le nombre d'anomalies billing disproportionné
4. "Brique 3" et "Mode demo" dans l'assistant achat

## Ce qui bloque une présentation investisseur
1. Les contradictions de chiffres entre pages (4 vs 5 briques, 78% vs 100%, 23k vs 209k)
2. Le prix fallback obsolète qui fausse le shadow billing
3. Le score Actions binaire qui ne reflète pas la réalité
4. La KB totalement vide

---

# 9. Recommandations classées

## P0 — Corriger immédiatement (avant toute démo)

| # | Action | Effort |
|---|--------|--------|
| P0-1 | **Redémarrer le backend** pour que les fixes P0 du sprint précédent prennent effet (connector descriptions + onboarding auto-detect) | 1 min |
| P0-2 | **Investiguer le bug onboarding auto-detect** — la chaîne Portefeuille→EntiteJuridique→Organisation ne trouve probablement pas les sites du seed. Vérifier que le seed crée bien les EntiteJuridique liées à l'org | 30 min |
| P0-3 | **Réduire le ratio anomalies/factures** — calibrer le seed pour que ~20% des factures (7-8 sur 36) aient des anomalies, pas 52 multi-règles. Ajuster les seuils ou le seed | 1h |
| P0-4 | **Supprimer "Brique 3 — Post-ARENH v3.0.0"** du titre Assistant Achat — remplacer par "Assistant Achat Énergie" simple | 5 min |
| P0-5 | **Masquer "Mode demo"** checkbox dans Assistant Achat | 5 min |
| P0-6 | **Corriger les 15 accents manquants** les plus visibles (activation, status, connectors, renouvellements) | 30 min |

## P1 — Corriger vite (cette semaine)

| # | Action | Effort |
|---|--------|--------|
| P1-1 | Ajouter pagination au Diagnostic conso (20 lignes par page) | 1h |
| P1-2 | Seeder des contrats pour tous les 5 sites dans le pack helios (pas juste Siege HELIOS Paris) | 1h |
| P1-3 | Seeder 10-15 items KB/Mémobox (règles BACS, DT, APER, tarifs) | 2h |
| P1-4 | Remplacer le score Actions binaire (55/80) par un calcul continu | 1h |
| P1-5 | Actualiser les dates des notifications au seed (relative à today, pas figées en 2025) | 30 min |
| P1-6 | Mettre à jour le prix fallback 0.068→0.15 €/kWh dans shadow billing | 5 min |
| P1-7 | Harmoniser "4 briques activées" (cockpit) vs "5/5 briques actives" (activation) | 30 min |
| P1-8 | Clarifier "Couverture 78%" vs "100% des sites" — ajouter tooltip explicatif | 15 min |

## P2 — Corriger ensuite

| # | Action | Effort |
|---|--------|--------|
| P2-1 | Paginer la liste de factures en bas de Bill Intel | 1h |
| P2-2 | Clarifier "Non détecté" sur Performance (→ "Pas de gaspillage détecté") | 5 min |
| P2-3 | Compléter le questionnaire Segmentation (pré-remplir pour la démo) | 15 min |
| P2-4 | Calibrer le risque financier par surface (pas flat-rate 7500€) | 2h |
| P2-5 | Ajouter pondération surface dans le tooltip du score conformité | 15 min |
| P2-6 | Rendre les "Scopes O:1" plus lisibles dans Admin Users | 30 min |

## Surveiller seulement

- Badge "10" sur Performance — vérifier que ce nombre a du sens
- Risque patrimoine "209 k€" vs cockpit "23 k€" — documenter la différence
- Console.log en mode dev — acceptable mais nettoyer avant production

---

# 10. Plan priorisé

| Ordre | Action | Impact | Effort | Pourquoi maintenant |
|-------|--------|--------|--------|---------------------|
| 1 | Redémarrer backend + vérifier fixes P0 sprint | Critique | 1 min | Les fixes existent dans le code mais ne sont pas actifs |
| 2 | Fix onboarding auto-detect (debug chaîne Portefeuille→EJ→Org) | Critique | 30 min | 0/6 est la première chose qu'un prospect voit |
| 3 | Masquer "Brique 3" + "Mode demo" dans Assistant Achat | Critique | 10 min | Labels POC visibles |
| 4 | Calibrer seed billing (ratio anomalies → ~20% max) | Critique | 1h | 52 anomalies / 36 factures = non crédible |
| 5 | Corriger accents (15 occurrences prioritaires) | Élevé | 30 min | Amateur pour B2B France |
| 6 | Pagination Diagnostic conso | Élevé | 1h | Page inutilisable sans |
| 7 | Seeder contrats tous sites + KB items | Élevé | 2h | Modules Achat et KB semblent vides |
| 8 | Score Actions continu + prix fallback | Moyen | 1h | KPI plus crédibles |
| 9 | Dates notifications relatives | Moyen | 30 min | Alertes 2025 en mars 2026 |
| 10 | Harmoniser briques/couverture cockpit vs activation | Moyen | 30 min | Contradictions inter-pages |

---

# 11. Verdict final

## PROMEOS est-il réellement crédible aujourd'hui ?

**Oui, à 80%.** La richesse fonctionnelle est impressionnante : 27 pages réelles, 0 route morte, 5 modules cohérents, shadow billing V2, scénarios d'achat, heatmap usages, conformité multi-framework. C'est un vrai produit, pas un POC.

**Mais les 20% restants sont les 20% qui comptent en démo :** l'onboarding qui dit 0/6, le mot "stub" qui trahit un brouillon, le ratio anomalies/factures qui détruit la crédibilité du moteur, et les labels internes ("Brique 3", "Mode demo") qui rappellent que c'est un environnement de dev.

## Qu'est-ce qui empêche encore un effet "top world" ?

1. **La calibration du seed** — les données de démo doivent raconter une histoire cohérente : un portefeuille sain avec quelques anomalies réalistes, pas un système qui alerte sur tout
2. **Les contradictions inter-pages** — un prospect qui navigue entre Cockpit, Activation et Patrimoine voit des chiffres qui ne concordent pas (4 vs 5 briques, 78% vs 100%, 23k vs 209k)
3. **Le polish final** — accents, labels, dates, "stub", "Brique 3" — ce sont des détails mais un prospect exigeant les remarque en 30 secondes

## Qu'est-ce qui doit être corrigé AVANT toute nouvelle feature ?

1. Onboarding auto-detect fonctionnel
2. Zéro occurrence de "stub" dans l'UI
3. Ratio anomalies/factures ≤ 30%
4. Labels internes masqués ("Brique 3", "Mode demo")
5. Accents corrigés sur les pages les plus visibles

## Qu'est-ce qui doit être gelé car déjà assez bon ?

- **Usages Horaires** — world-class, ne pas toucher
- **Achat Énergie scénarios** — excellent storytelling
- **Sidebar/navigation** — architecture solide
- **Cockpit structure** — bon design (corriger les chiffres, pas le layout)
- **Conformité** — frise + score + plan d'action bien structurés
- **Admin Users** — propre et fonctionnel

## Si tu devais montrer PROMEOS demain à un prospect exigeant, qu'est-ce qui te ferait peur ?

1. **Qu'il clique sur Onboarding** et voie 0/6 → "votre produit ne sait pas ce qui est installé"
2. **Qu'il ouvre les Connecteurs** et voie "(stub)" → "ce n'est pas un vrai produit"
3. **Qu'il demande "pourquoi 52 anomalies?"** → pas de réponse crédible
4. **Qu'il ouvre l'Assistant Achat** et voie "Brique 3 — Post-ARENH v3.0.0" → "c'est quoi ce jargon?"
5. **Qu'il ouvre la KB** et voie 0 items → "votre base de connaissances est vide"

**Score final : 71/100 — Potentiel 88/100 avec les 10 actions du plan priorisé.**

---

*Audit réalisé le 2026-03-11 par quatuor Lead Product Auditor + UX/UI Principal + Functional QA + Senior Architect.*
*Méthode : Playwright headless 27 pages + 3 agents code (routing 69 routes, KPI 12 services, wording 500+ fichiers) + vérification API live.*
