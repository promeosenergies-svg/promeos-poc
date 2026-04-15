# AUDIT PRODUIT COMPLET — PROMEOS POC
**Date** : 8 mars 2026
**Méthode** : Analyse visuelle (19 screenshots Playwright 1920x1080) + audit code source (6 agents spécialisés, ~109 findings)
**Périmètre** : Toutes les pages accessibles du POC, navigation desktop, données démo Helios
**Évaluateur** : Claude Opus 4.6, audit automatisé exhaustif

---

## 1. EXECUTIVE SUMMARY

PROMEOS est une plateforme SaaS de gestion énergétique ambitieuse couvrant patrimoine, consommation, facturation, achat d'énergie, conformité et actions. Le POC démontre une **couverture fonctionnelle impressionnante** (17 pages fonctionnelles sur 19 tentées) avec des données réalistes et une UI cohérente basée sur Tailwind + Lucide.

**Points forts majeurs** :
- Cockpit exécutif riche avec score 40/100, KPIs agrégés, priorisation risque
- Shadow billing innovant (recalcul attendu vs facturé, détection d'anomalies)
- Patrimoine avec heatmap risque visuelle, scores par site
- Diagnostic conso automatique avec alertes colorées et recommandations
- Portefeuille conso multi-site avec comparaison

**Verdict global** : **6.5/10** — Fonctionnellement riche mais souffrant de problèmes de navigation, de pages mortes, d'états vides non guidants, et de densité d'information qui nuisent à la démonstration. Avec les 15 corrections prioritaires ci-dessous, le score pourrait atteindre 8.5/10.

---

## 2. TOP 10 PROBLÈMES CRITIQUES

| # | Sévérité | Page | Problème | Impact |
|---|----------|------|----------|--------|
| 1 | **BLOQUANT** | /assistant-achat | **Page introuvable (404)** — route cassée, le lien existe dans la nav | Prospect voit une erreur. Perte de crédibilité immédiate |
| 2 | **BLOQUANT** | /marche | **Page introuvable (404)** — route cassée | Idem, 2 pages mortes sur 19 = 10.5% de taux d'erreur |
| 3 | **CRITIQUE** | /monitoring | **État vide "Sélectionnez un site"** sans auto-sélection | Page entièrement blanche à l'arrivée. Prospect ne comprend pas |
| 4 | **CRITIQUE** | /usages-horaires | **État vide "Aucun site sélectionné"** sans auto-sélection | Même problème — page vide, aucune guidance |
| 5 | **CRITIQUE** | /bill-intel | **Page extrêmement longue** — scroll infini avec 50+ factures visibles | Densité écrasante. Le tableau factures noie les anomalies (la valeur) |
| 6 | **MAJEUR** | /achat-energie | **"Aucun scénario calculé"** — état vide peu guidant | L'action "Comparer les scénarios" est visible mais le résultat est vide |
| 7 | **MAJEUR** | Sidebar | **"Incomplet" badge orange** affiché en permanence dans le header | Signal anxiogène pour un prospect. Pas d'explication de ce que ça signifie |
| 8 | **MAJEUR** | Navigation | **Sidebar se collapse** sur certaines pages (achat, admin) — items cachés | Perte de repères, l'utilisateur ne sait plus où il est |
| 9 | **MAJEUR** | /cockpit | **Tooltip/popover bloquant** visible sur le screenshot — masque du contenu | Artefact UI qui nuit à la capture d'écran et potentiellement à l'usage |
| 10 | **MODÉRÉ** | /conformite | **7 onglets visibles** — surcharge cognitive pour un nouvel utilisateur | Obligations, Données, Estimations, Plan d'actions, Plan d'exécution, Process, Véhic... |

---

## 3. AUDIT DÉTAILLÉ PAR SECTION

### 3.1 Navigation & Layout

**Screenshot de référence** : Toutes les pages (sidebar gauche)

**Observations visuelles** :
- Sidebar gauche avec 5 icônes principales (Pilotage, Patrimoine, Énergie, Achat, panier)
- Breadcrumb présent en haut : `PROMEOS > Section > Page`
- Scope selector "Groupe HELIOS - Tous les sites" avec dropdown
- Barre de recherche + toggle Expert en haut à droite
- Badge "Incomplet" orange visible sur toutes les pages
- Section "RÉCENTS" dans la sidebar montre les dernières pages visitées

**Points positifs** :
- Breadcrumb cohérent et fonctionnel
- Icônes latérales reconnaissables
- Scope selector bien visible

**Problèmes identifiés** :

| # | Sévérité | Constat |
|---|----------|---------|
| N1 | CRITIQUE | **2 routes mortes** : `/assistant-achat` et `/marche` retournent "Page introuvable" avec un bouton "Retour au Command Center" |
| N2 | MAJEUR | **Sidebar inconsistante** : sur /achat-energie, seuls PILOTAGE/PATRIMOINE/ÉNERGIE/ACHAT sont visibles avec "Stratégies d'achat" en sous-menu. Sur /cockpit, la sidebar montre Cockpit, Centre d'actions, Notifications, Patrimoine, etc. Le modèle mental change selon la section |
| N3 | MAJEUR | **Badge "Incomplet"** affiché partout sans explication. Qu'est-ce qui est incomplet ? L'onboarding ? Les données ? Aucun lien vers la résolution |
| N4 | MODÉRÉ | **Pas de highlight actif clair** dans la sidebar pour la page courante sur certaines sections (ex: /achat-energie, la sidebar ne montre pas clairement "Stratégies d'achat" comme actif) |
| N5 | MODÉRÉ | **Section ADMINISTRATION** en bas de sidebar visible mais collapsée — pas évident qu'il y a du contenu dedans |

**Score Navigation** : 5/10

---

### 3.2 Cockpit (Vue exécutive)

**Screenshot** : 01-cockpit.png

**Observations** :
- Titre "Vue exécutive" avec badge rouge "Groupe HELIOS - 5 sites"
- 4 alertes prioritaires en haut (risque conformité, optimisations, etc.)
- Score global 40/100 avec gauge visuelle
- KPIs : 23 k€, 63%, 100%
- Tooltip/popover "KPIs essentiels" visible (semble être un overlay d'aide)
- Section "4 Alertes critiques" avec tableau
- Section "Priorité: réduire le risque conformité" avec call-to-action
- Badges DPE par site (A, B, C, D, E)
- Tableau des sites avec colonnes : Ville, Surface, Conformité, Risque, Budget

**Points positifs** :
- Dense mais hiérarchisé — les alertes sont en haut
- Score 40/100 donne un ancrage immédiat
- Call-to-action "Voir le plan à 6 mois" est clair
- KPIs bien espacés avec tendances (flèches)

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| C1 | MODÉRÉ | **Tooltip/overlay bloquant** — un popover "KPIs essentiels" est affiché et masque du contenu. En démo, c'est distrayant |
| C2 | MODÉRÉ | **Score 40/100 sans explication** visible immédiatement — qu'est-ce qui fait baisser ? Le lien avec les 4 indicateurs (conformité, risque, maturité, couverture) n'est pas immédiat |
| C3 | MINEUR | **"ACTIVATIONS DU DOMAINE"** en bas — jargon technique, pas clair pour un DG |
| C4 | MINEUR | Le tableau sites est tronqué, il faut scroller. La pagination "1-5 sur 5" est visible mais le tableau prend beaucoup de place |

**Score Cockpit** : 7.5/10

---

### 3.3 Patrimoine

**Screenshot** : 02-patrimoine.png

**Observations** :
- Titre "Patrimoine" avec "5 sites, +17 047 m², 2 conformités, 23 pts de risque"
- Risque global 205 k€ avec badges rouge/vert
- Heatmap horizontale par site (couleurs rouge/orange/jaune/vert)
- Cards par site avec score risque (Hotel Helios Nice: 110 k€, Siege HELIOS Paris: 48 k€)
- Section "Profil Energies" avec badge "Tertiaire Privé 6%"
- Tableau détaillé avec colonnes : Conformité, DPE, Surface, Compteurs

**Points positifs** :
- Heatmap risque très visuelle — on comprend immédiatement quels sites sont à risque
- Cards site bien structurées avec score
- Bonne utilisation des couleurs (rouge=danger, vert=OK)

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| P1 | MODÉRÉ | **"Profil Energies — Tertiaire Privé 6%"** — le 6% n'est pas expliqué (6% de quoi ?) |
| P2 | MODÉRÉ | **Tableau en bas** mélange conformité (Conforme/Non-conforme) avec DPE et surface — beaucoup de colonnes pour un écran |
| P3 | MINEUR | **"23 k€" de risque** dans les KPIs du haut vs **"205 k€"** dans le risque global — confusion entre les deux chiffres |

**Score Patrimoine** : 8/10

---

### 3.4 Conformité réglementaire

**Screenshot** : 03-conformite.png

**Observations** :
- Titre "Conformité réglementaire" avec "Groupe HELIOS - 7 organisations, 6 rated"
- Points d'attention en haut avec call-to-action
- Badge rouge "Conformité faible (2/10). Actions urgentes requises."
- **7 onglets** : Obligations, Données & Qualité, Estimations, Plan d'actions, Plan d'exécution, Process, Véhic...
- Gauge 0% avec status "Non conforme" (1), "Conforme" (0), "A qualifier" (4)
- Section "Obligations en retard — échéance dépassée" avec code couleur rouge
- Détails obligations : BACS (07/04/72), Decret Tertiaire, Loi APER (GHG)
- Chaque obligation a : Sites concernés, Conformité (2/5), Échéance, liens "Voir action"

**Points positifs** :
- Urgence bien communiquée (rouge, badges "Urgent")
- Détail par obligation clair
- Call-to-action "Voir le plan d'actions" et "Voir le plan économique" présents

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| CF1 | MAJEUR | **7 onglets** dont le dernier tronqué ("Véhic...") — surcharge massive. Un nouvel utilisateur ne sait pas par où commencer |
| CF2 | MODÉRÉ | **Date d'échéance BACS : 07/04/72** — semble être une erreur de données (1972 ou 2072 ?) |
| CF3 | MODÉRÉ | **Gauge 0%** + "1 réglé, 1 actif, 1 aide" sous la gauge — les labels ne correspondent pas aux segments |
| CF4 | MINEUR | **"A qualifier" (4)** — pas clair ce que l'utilisateur doit faire pour qualifier |

**Score Conformité** : 6.5/10

---

### 3.5 Consommations (Explorer + Portefeuille + Diagnostic)

**Screenshots** : 04-consommations.png, 05-explorer.png, 06-diagnostic.png, 08-portfolio-conso.png

#### 3.5.1 Explorer

**Observations** :
- Tab bar en haut : Explorer (actif), Portefeuille, Import & Analyse, Météo/Rétro
- Titre "Explorateur de consommation" avec sous-titre explicatif
- Cross-nav links : Diagnostic, Performance (en haut à droite)
- Filtres : Énergie (Électricité/Gaz), site selector, période
- KPIs : 531 134 kWh, 85 151 EUR, 160.10 EUR/MWh, 27 640 kg CO2, 240 kW
- Graphique barres bleu avec courbe de charge
- Toggle "Mode Expert →" avec micro-explication

**Points positifs** :
- Tab bar clarifie la navigation entre sous-pages conso
- Cross-nav vers Diagnostic et Performance = excellent
- KPIs bien formatés avec unités
- Graphique lisible

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| EX1 | MODÉRÉ | **"Siège HELIOS Paris — 43707 (elec_gaz, electricity)"** dans le titre du graphique — chaîne technique visible à l'utilisateur (ID compteur, type brut) |
| EX2 | MODÉRÉ | **"Mode Expert →"** toggle — le micro-texte "Signature, météo, tunnel, objectifs" est utile mais très petit (10px), facile à rater |
| EX3 | MINEUR | **"4707 lignes"** visible en bas — info technique pas utile pour un utilisateur métier |

#### 3.5.2 Portefeuille

**Observations** :
- KPIs agrégés : 3 952 499 kWh, 711 450 EUR, 205 530 kg CO2, 5/5 sites
- Badge "Couverture 98%" en haut à droite
- Section "Ce qui en priorité" : Impact financier, Dérives détectées, Consommation nocturne
- Tableau multi-site avec colonnes nombreuses

**Points positifs** :
- Vue portefeuille donne la big picture immédiatement
- Priorisation par impact financier = bonne approche

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| PF1 | MODÉRÉ | **Tableau très large** avec ~12 colonnes — nécessite scroll horizontal implicite |
| PF2 | MINEUR | **"Couverture 98%"** — de quoi ? Des compteurs ? Des périodes ? Pas explicité |

#### 3.5.3 Diagnostic

**Observations** :
- 4 alertes en haut avec badges colorés
- KPIs : 13 alertes, 368 k€ impact estimé, 120 617 kg CO2
- Tableau d'alertes avec type, source, message, impact, dates
- Badges colorés : "Fiche anormale" (rouge), "Valeur Seuil" (orange), "Dérive consommation" (jaune)

**Points positifs** :
- Alertes bien catégorisées avec impact financier
- Messages explicites en français ("Pic de consommation anormal à 7 648 kWh")
- Tri par date et filtrage par type

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| DG1 | MODÉRÉ | **Messages très longs** tronqués dans le tableau — ex "Dérive de la consommation à +12% (+15% de la moyenne basse saison)" |
| DG2 | MINEUR | Pas de lien direct vers le compteur/site depuis l'alerte |

**Score Consommations** : 7.5/10

---

### 3.6 Performance / Monitoring

**Screenshot** : 07-monitoring.png

**Observations** :
- Titre "Performance Électrique — KPIs, puissance, qualité de données & alertes"
- Dropdown "Choisir un site..." en haut à droite
- **Page entièrement vide** : icône + "Sélectionnez un site"
- Message : "Choisissez un site dans le sélecteur ci-dessus pour voir les KPIs de performance électrique."
- Badge "(10)" visible dans la sidebar à côté de "Performance"

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| MO1 | **CRITIQUE** | **Page vide à l'arrivée** — aucune auto-sélection du premier site. En démo, c'est catastrophique. Un prospect voit un écran blanc. |
| MO2 | MODÉRÉ | **Badge (10)** dans la sidebar suggère 10 items mais la page est vide — contradiction |
| MO3 | MINEUR | Le message d'aide est correct mais pourrait être un CTA cliquable vers le premier site |

**Score Monitoring** : 3/10

---

### 3.7 Facturation (Bill Intel + Timeline)

**Screenshots** : 09-bill-intel.png, 10-billing-timeline.png

#### 3.7.1 Bill Intel (Anomalies & Audit)

**Observations** :
- Tab bar : "Anomalies & Audit" (actif), "Timeline & Couverture"
- Message d'intro : "PROMEOS recalcule le montant attendu de chaque facture en croisant le contrat, la conso réelle et les tarifs réglementaires..."
- KPIs : 1 264 643 €, 3 437 254 €, 12 anomalies, 34 645 € d'écart
- Section "Anomalies détectées (12)" avec cards détaillées
- Chaque anomalie : badge type (surfacturation, sous-facturation), site, montants, écart, boutons
- **Très long scroll** : section anomalies puis tableau "Factures (61)" avec toutes les factures

**Points positifs** :
- Tab bar fonctionne bien — passage fluide vers Timeline
- Badges type d'anomalie colorés et lisibles
- Shadow billing concept bien présenté dans l'intro

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| BI1 | **CRITIQUE** | **Page extrêmement longue** — les 61 factures sont affichées dans un tableau interminable. La valeur (anomalies) est noyée dans la masse. Le screenshot fait ~3000px de haut |
| BI2 | MAJEUR | **Aucune pagination** visible sur le tableau factures — tout est chargé d'un coup |
| BI3 | MODÉRÉ | **Double information** : les anomalies sont en cards en haut ET dans le tableau en bas — le lien entre les deux n'est pas évident |
| BI4 | MODÉRÉ | KPI "12" anomalies mais les cards en dessous disent "Anomalies détectées (12)" — redondant |

#### 3.7.2 Timeline

**Observations** :
- Tab bar : "Anomalies & Audit" (lien), "Timeline & Couverture" (actif)
- Titre "Facturation — Timeline" avec sous-titre explicatif
- Barre de couverture verte (timeline)
- KPIs agrégés : Facturées, Couvert, Manquant, Partiel
- Timeline mensuelle : Décembre 2025 → Janvier 2025, chaque mois avec "Couvert" badge
- Chaque mois montre : nombre factures, montant total

**Points positifs** :
- Vue timeline claire et intuitive
- Barre de progression verte rassurante
- Tab bar bien intégré

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| TL1 | MINEUR | Pas d'interaction visible — cliquer sur un mois ne semble pas mener à un détail |

**Score Facturation** : 6.5/10

---

### 3.8 Achat d'énergie

**Screenshots** : 11-achat-energie.png, 12-assistant-achat.png

#### 3.8.1 Stratégies d'achat

**Observations** :
- 4 onglets : Simulation (actif), Portefeuille, Échéances, Historique
- Badge "Confiance : Faible" (rouge)
- Section "Sélection du site & Estimation" : dropdown site, volume estimé 1 736 548 kWh/an, profil de charge 1.25
- Section "Hypothèses" : Volume, Horizon (24 mois), Énergie (Électricité)
- Section "Préférences" : Tolérance risque (Faible/Moyen/Élevé), Priorité budget (slider), Offre verte
- Section "Décalage heures pleines → solaire" avec "TARIF HEURES SOLAIRES"
- Bouton "Comparer les scénarios"
- **État vide** : "Aucun scénario calculé"

**Points positifs** :
- UI de simulation bien structurée — paramètres clairs
- Slider priorité budget visuel
- Toggle risque intuitif

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| AE1 | MAJEUR | **"Aucun scénario calculé"** — en démo, il faudrait des scénarios pré-calculés. Le prospect ne va pas cliquer "Comparer" pendant la démo |
| AE2 | MODÉRÉ | **"Confiance : Faible"** badge rouge — anxiogène. Pourquoi faible ? Pas d'explication immédiate |
| AE3 | MODÉRÉ | **"Post-ARENH — élec uniquement"** — jargon métier sans explication |
| AE4 | MINEUR | **"Décalage heures pleines → solaire"** avec icône signal rouge — pas clair ce que ça fait |

#### 3.8.2 Assistant Achat

**Observation** : **PAGE INTROUVABLE (404)**
- "La page « /assistant-achat » n'existe pas ou a été déplacée."
- Bouton "Retour au Command Center"

| # | Sévérité | Constat |
|---|----------|---------|
| AA1 | **BLOQUANT** | Route `/assistant-achat` référencée mais inexistante. Lien mort. |

**Score Achat** : 4.5/10

---

### 3.9 Renouvellements contrats

**Screenshot** : 13-renouvellements.png

**Observations** :
- Titre "Renouvellements contrats" avec sous-titre
- Filtres en ligne : EL, RL, Fournisseur, Fin contrat, Loyer, Audit
- Toggle "Tertiaire Privé / XPS"
- Bannière "Profil à 37% — répondez à 2 questions pour affiner vos contrats"
- Tableau : Site, Fournisseur, Fin, Mensualité, Type contrat, État (badges colorés), Éligible, Priorité

**Points positifs** :
- Tableau structuré avec colonnes pertinentes
- Badges d'état colorés (Spot, En cours, etc.)
- Priorité visible par site

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| RN1 | MODÉRÉ | **"Profil à 37%"** — même concept que le badge "Incomplet" mais avec un % différent. Quelle est la relation ? |
| RN2 | MODÉRÉ | **Colonnes "Pro Flex", "ARENH Secure"** — termes produits spécifiques sans explication |
| RN3 | MINEUR | Certaines cellules vides (mensualité manquante) sans indication "N/A" ou "—" |

**Score Renouvellements** : 7/10

---

### 3.10 Plan d'actions

**Screenshot** : 14-actions.png

**Observations** :
- Titre "Plan d'actions" avec "11 actions - 81 902 EUR (Impact total)"
- KPIs : En cours 7, Impact direct 0, Terminées 4, En pause 0
- Filtres : Recherche, type (Toutes types)
- Badge "Exporter (15)" en haut à droite
- Tableau : Action, Type (Tertiaire/Conformité), Priorité (Site 1-3), Impact EUR, Ville, Échéance, Responsable, Statut
- Statuts colorés : Terminée (vert), À planifier (orange)
- Pagination "11 sur 11"

**Points positifs** :
- Vue tableau classique et fonctionnelle
- Priorisation par site claire
- Export disponible
- Responsable assigné par action

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| AC1 | MODÉRÉ | **KPI "Impact direct: 0"** — surprenant avec 81 902 EUR d'impact total. Incohérence des métriques |
| AC2 | MODÉRÉ | **"Site 1", "Site 2", "Site 3"** comme priorité — pas immédiatement compréhensible (c'est un ranking, pas un nom de site) |
| AC3 | MINEUR | Pas de vue Kanban ou timeline — uniquement un tableau |

**Score Actions** : 7.5/10

---

### 3.11 Notifications / Alertes

**Screenshot** : 15-notifications.png

**Observations** :
- Titre "Alertes" avec "29 alertes, 10 nouvelles"
- KPIs : Critiques 11, Non lues 5
- Filtres : Toutes (29), Nouvelles (10), Lues (4), Ignorées (0)
- Tableau : Code, Type, Description, Impact EUR, Estimé, Statut
- Types variés : hausse tarif, conformité, anomalie facture, contrat expiration, etc.
- Badge icônes colorés par type d'alerte

**Points positifs** :
- Bonne variété d'alertes (multi-domaine)
- Impact financier pour chaque alerte
- Filtrage par statut fonctionnel

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| NT1 | MODÉRÉ | **29 alertes non paginées** — tout est dans un seul scroll |
| NT2 | MINEUR | Pas de groupement par type ou date — liste plate |

**Score Notifications** : 7/10

---

### 3.12 Administration (Users)

**Screenshot** : 16-admin-users.png

**Observations** :
- Titre "Utilisateurs" avec "1 utilisateur"
- Tableau : Utilisateur, Email, Role (DG / Owner), Scopes (O:1), Statut (Actif), Dernière connexion
- Seul utilisateur : Promeos Admin

**Points positifs** :
- Interface propre et fonctionnelle
- Informations essentielles présentes

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| AD1 | MINEUR | **"Scopes O:1"** — jargon technique, devrait afficher "Organisation: Groupe HELIOS" |
| AD2 | MINEUR | Pas de bouton "Inviter un utilisateur" visible immédiatement |

**Score Admin** : 7/10

---

### 3.13 Onboarding

**Screenshot** : 17-onboarding.png

**Observations** :
- Titre "Demarrage" (sans accent) avec "Configurez votre plateforme en 6 étapes"
- Barre de progression 0/6 = 0%
- 6 étapes : Créer l'organisation, Ajouter des sites, Connecter les compteurs, Importer les factures, Inviter les utilisateurs, Créer une action
- Chaque étape : description + bouton "Configurer" + "Marquer terminé"

**Points positifs** :
- Wizard linéaire clair
- 6 étapes bien séquencées et logiques
- Progression visible

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| OB1 | MODÉRÉ | **"Demarrage"** au lieu de **"Démarrage"** — faute d'orthographe dans le titre principal |
| OB2 | MODÉRÉ | **"Creer l'organisation"** — manque l'accent ("Créer") dans le titre d'étape 1 |
| OB3 | MODÉRÉ | **0% en démo** — en mode démo avec données seedées, l'onboarding devrait détecter les étapes déjà faites |
| OB4 | MINEUR | Bouton "Détection auto" en haut à droite — pas évident ce que ça fait |

**Score Onboarding** : 6.5/10

---

### 3.14 Marché

**Screenshot** : 18-marche.png

**Observation** : **PAGE INTROUVABLE (404)**

| # | Sévérité | Constat |
|---|----------|---------|
| MR1 | **BLOQUANT** | Route `/marche` référencée dans la nav mais inexistante |

**Score Marché** : 0/10

---

### 3.15 Usages Horaires

**Screenshot** : 19-usages-horaires.png

**Observations** :
- Titre "Usages & Horaires — Profil conso · Anomalies comportementales"
- **Page vide** : "Aucun site sélectionné"
- Pas de sélecteur de site visible

**Problèmes** :

| # | Sévérité | Constat |
|---|----------|---------|
| UH1 | **CRITIQUE** | **Page vide sans sélecteur de site visible** — comment l'utilisateur choisit-il un site ? |
| UH2 | MODÉRÉ | Pas d'auto-sélection du premier site disponible |

**Score Usages Horaires** : 2/10

---

## 4. CONTRADICTIONS ET PERTES DE CONFIANCE

| # | Type | Détail | Pages concernées |
|---|------|--------|------------------|
| X1 | **Données incohérentes** | Risque "23 k€" dans le cockpit vs "205 k€" dans Patrimoine — ce sont des métriques différentes mais pas expliqué | Cockpit, Patrimoine |
| X2 | **Routes mortes** | 2 pages sur 19 retournent 404 alors qu'elles sont référencées dans la navigation | /assistant-achat, /marche |
| X3 | **Badge "Incomplet"** | Affiché en permanence sur toutes les pages sans explication ni action de résolution | Global |
| X4 | **Onboarding 0%** | Le mode démo a des données seedées (5 sites, compteurs, factures) mais l'onboarding indique 0% | /onboarding |
| X5 | **"Confiance: Faible"** | Sur Achat énergie, le badge est rouge sans justification. En démo avec données complètes, ça devrait être au moins "Moyenne" | /achat-energie |
| X6 | **Impact direct 0** | Plan d'actions montre 81 902 EUR d'impact total mais "Impact direct: 0" — métriques contradictoires | /actions |
| X7 | **Pages vides** | Monitoring et Usages Horaires montrent des pages vides alors que des données existent pour les sites | /monitoring, /usages-horaires |
| X8 | **Sidebar (10)** | Le badge "(10)" apparaît à côté de "Performance" dans la sidebar mais la page est vide | /monitoring sidebar |
| X9 | **Login hint incorrect** | La page de login affiche "sophie@atlas.demo / demo2024" mais ce credential ne fonctionne pas sur le backend | /login |

---

## 5. MODÈLE MENTAL & NAVIGATION

### Architecture de navigation observée

```
PILOTAGE
├── Cockpit (Vue exécutive)
├── Centre d'actions (Plan d'actions)
├── Notifications (Alertes)

PATRIMOINE
├── Sites & Bâtiments
├── Conformité

ÉNERGIE
├── Consommations
│   ├── Explorer (tab)
│   ├── Portefeuille (tab)
│   ├── Import & Analyse (tab)
│   └── Météo/Rétro (tab)
├── Performance (Monitoring)
├── Facturation
│   ├── Anomalies & Audit (tab)
│   └── Timeline & Couverture (tab)

ACHAT
├── Stratégies d'achat
│   ├── Simulation (tab)
│   ├── Portefeuille (tab)
│   ├── Échéances (tab)
│   └── Historique (tab)
├── [Assistant Achat → 404]
├── Renouvellements

ADMINISTRATION
├── Utilisateurs

PAGES NON NAVIGUABLES DIRECTEMENT
├── Onboarding
├── [Marché → 404]
├── Usages Horaires
├── Diagnostic conso (accessible via cross-nav depuis Explorer)
```

### Analyse du modèle mental

**Ce qui fonctionne** :
- La hiérarchie PILOTAGE > PATRIMOINE > ÉNERGIE > ACHAT suit un flux logique "top-down"
- Les tabs internes (Conso, Billing, Achat) groupent bien les sous-vues
- Le breadcrumb confirme la position

**Ce qui pose problème** :
1. **Confusion Consommations/Performance/Diagnostic** : 3 concepts proches dispersés. Un utilisateur cherchant "mes consommations ont un problème" doit naviguer entre Explorer, Diagnostic, et Monitoring
2. **Facturation splitée** : Pourquoi 2 vues (Anomalies + Timeline) ? Un prospect pense "facturation" = une page
3. **Sidebar dynamique** : Le contenu de la sidebar change selon la section — parfois elle montre "RÉCENTS", parfois pas. Perte de repères
4. **Pages orphelines** : Onboarding, Usages Horaires et Diagnostic conso ne sont pas dans la sidebar principale — accessibles uniquement par URL directe ou cross-nav

---

## 6. RECOMMANDATIONS STRUCTURANTES

### R1 — Éliminer les pages mortes (URGENT)
Supprimer ou connecter `/assistant-achat` et `/marche`. Soit créer les pages, soit retirer les routes et les liens.

### R2 — Auto-sélection du premier site
Sur toutes les pages site-dépendantes (Monitoring, Usages Horaires), auto-sélectionner le premier site si aucun n'est choisi. Afficher immédiatement des données.

### R3 — Paginer le tableau factures
Sur BillIntelPage, limiter le tableau factures à 10-20 items avec pagination. La page actuelle est inexploitable à 61 lignes.

### R4 — Pré-calculer les scénarios démo
Sur Achat énergie, avoir au moins 2-3 scénarios pré-calculés (Fixe, Indexé, Spot) pour le mode démo.

### R5 — Supprimer ou expliquer "Incomplet"
Le badge "Incomplet" doit soit disparaître en mode démo, soit devenir cliquable avec une explication de ce qui manque.

### R6 — Synchroniser l'onboarding avec les données
En mode démo, l'onboarding devrait refléter les étapes déjà complétées (sites ajoutés, compteurs connectés, etc.).

### R7 — Corriger l'orthographe
"Demarrage" → "Démarrage", "Creer" → "Créer". Petits détails mais critiques pour la crédibilité.

### R8 — Réduire les onglets conformité
7 onglets → 4 max. Grouper "Plan d'actions + Plan d'exécution" et "Process + Véhicules" sous des sous-menus.

### R9 — Corriger le login hint
Remplacer "sophie@atlas.demo / demo2024" par les vrais credentials démo qui fonctionnent.

### R10 — Clarifier les KPIs contradictoires
Ajouter des tooltips ou sous-titres expliquant la différence entre "risque 23 k€" (cockpit) et "risque 205 k€" (patrimoine).

---

## 7. PLAN D'ACTION PRIORISÉ

### Sprint immédiat (1-2 jours) — "Fix the Broken"

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | Supprimer/fixer routes `/assistant-achat` et `/marche` | XS | Bloquant |
| 2 | Auto-sélection premier site sur Monitoring + Usages Horaires | S | Critique |
| 3 | Corriger login hint (sophie → promeos credentials) | XS | Modéré |
| 4 | Corriger orthographe Onboarding ("Démarrage", "Créer") | XS | Modéré |

### Sprint court (3-5 jours) — "Demo-Ready"

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 5 | Paginer tableau factures BillIntel (20 items/page) | S | Critique |
| 6 | Pré-calculer 3 scénarios démo sur Achat énergie | M | Majeur |
| 7 | Masquer badge "Incomplet" en mode démo OU le rendre cliquable | S | Majeur |
| 8 | Synchro onboarding avec données existantes en démo | M | Majeur |
| 9 | Nettoyer chaînes techniques ("43707 elec_gaz electricity") | S | Modéré |

### Sprint moyen (1-2 semaines) — "Polish & Confidence"

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 10 | Réduire tabs conformité (7 → 4) | M | Majeur |
| 11 | Ajouter tooltips KPIs cockpit vs patrimoine | S | Modéré |
| 12 | Grouper/paginer alertes notifications | S | Modéré |
| 13 | Vue Kanban optionnelle pour Actions | M | Nice-to-have |
| 14 | Ajouter interaction clic sur mois Timeline | S | Nice-to-have |
| 15 | Masquer "Scopes O:1" technique dans Admin | XS | Mineur |

---

## 8. VERDICT FINAL

### Scores par section

| Section | Score | Commentaire |
|---------|-------|-------------|
| Navigation & Layout | 5/10 | Routes mortes, sidebar inconsistante, badge "Incomplet" |
| Cockpit | 7.5/10 | Riche mais tooltip intrusif, score non expliqué |
| Patrimoine | 8/10 | Meilleure page du POC — visuelle, claire, actionnable |
| Conformité | 6.5/10 | 7 onglets, données suspectes (date 1972) |
| Consommations | 7.5/10 | Bon après les améliorations conso UX, chaînes techniques visibles |
| Monitoring | 3/10 | Page vide sans auto-sélection = rédhibitoire en démo |
| Facturation | 6.5/10 | Shadow billing innovant mais page trop longue |
| Achat énergie | 4.5/10 | UI bien conçue mais 404 + état vide + jargon |
| Renouvellements | 7/10 | Solide, quelques jargons |
| Actions | 7.5/10 | Fonctionnel, métriques à clarifier |
| Notifications | 7/10 | Bonne couverture, manque de structure |
| Admin | 7/10 | Minimal mais fonctionnel |
| Onboarding | 6.5/10 | Bon concept, orthographe + sync manquantes |
| Marché | 0/10 | 404 |
| Usages Horaires | 2/10 | Page vide, pas de sélecteur |

### Score global pondéré : **6.5/10**

### Conclusion

PROMEOS démontre une **ambition fonctionnelle remarquable** pour un POC : shadow billing, diagnostic automatique, scoring patrimoine, simulation achat, conformité réglementaire. La couverture est large et le design est cohérent (Tailwind + Lucide + palette bleue).

Les **3 urgences absolues** sont :
1. **Éliminer les 2 pages 404** (crédibilité)
2. **Auto-sélectionner les sites** sur les pages vides (démontrabilité)
3. **Paginer BillIntel** (utilisabilité)

Avec le sprint immédiat (1-2 jours, 4 fixes), le POC passe de "prototype avec des trous" à "démo solide". Avec le sprint court (3-5 jours), il devient **réellement démontrable à un prospect DG**.

Le produit a le potentiel d'un **8.5/10** une fois les corrections appliquées. La valeur métier est là — c'est l'emballage qui doit être à la hauteur.
