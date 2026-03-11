# AUDIT TOTAL PROMEOS — 10 Mars 2026 (V2 post-sprint P0/P1)

**Quatuor d'experts** : Lead Product Auditor / UX-UI Principal / Functional QA / Senior Architect

Captures : 27 pages + 6 interactions (Playwright 1920×1080, JWT auth, Chromium headless)

---

## 1. Executive Summary

**Note globale : 71/100** (+9 pts vs audit V1 à 62)

**Verdict** : Les corrections P0/P1 ont éliminé les kill shots les plus grossiers (footer POC, 1 user, onboarding 0/6 dans le code). Mais l'exécution est incomplète — le serveur tourne sur l'ancien code, et le problème systémique des volumes (160 actions, Bill Intel trop rouge) reste entier. PROMEOS n'est PAS encore montrable à un prospect exigeant.

**Niveau de maturité réel** : Beta+ — POC éliminé dans le code, pas encore dans l'expérience live.

**Potentiel après correction** : 82-85/100 (atteignable en 1 sprint concentré)

### 5 risques les plus graves

| # | Risque | Impact |
|---|--------|--------|
| 1 | **160 actions / 734k EUR pour 5 sites** — moteur sync_actions génère 148 actions automatiques | Perte immédiate de crédibilité prospect |
| 2 | **Onboarding 0/6 après seed** — le code de fix existe mais le serveur/DB n'est pas à jour | Premier contact raté |
| 3 | **Connecteurs "(stub)" visibles** — code fixé, serveur pas redémarré | Technique visible |
| 4 | **Bill Intel : 148 insights / 36 factures** = 4 anomalies par facture = tout est rouge | "Si tout est anomalie, rien n'est anomalie" |
| 5 | **Conformité 59/100 vs "0%" conforme global** — contradiction visible sur la même page | Chiffres contradictoires |

### 5 forces réelles

| # | Force |
|---|-------|
| 1 | **Explorateur de consommation** — 527 MWh, 84k EUR, graphe lisible, KPI bar solide, filtres. Fait "produit mature". |
| 2 | **Achat énergie + Scénarios** — 4 stratégies (Prix Fixe/Indexé/Spot/Heures Solaires), scoring 42/100, recommandation. Module le plus abouti. |
| 3 | **Usages & Horaires (Heatmap 7×24)** — Score 99, heatmap impressionnante, profil journalier. Visuel expert de haut niveau. |
| 4 | **Status page** — Footer "PROMEOS v1.0", Version 1.0.0, 6/6 checks OK. Kill shot éliminé. |
| 5 | **Admin Users** — 4 utilisateurs crédibles (DG/Owner, Energy Manager, Auditeur, Resp. Site), rôles visibles, emails réalistes. |

---

## 2. Note détaillée par dimension

| Dimension | Note /10 | Commentaire sévère |
|-----------|----------|-------------------|
| UX | 6.5 | Navigation propre via sidebar contextuelle, mais parcours Actions→Diagnostic→Notifications reste confus. Trop de pages (27) sans hiérarchie claire pour un prospect. |
| UI | 7.5 | Design system Tailwind cohérent, cards/badges/tables bien alignés. Densité parfois excessive (Cockpit) ou excessive vide (Renouvellements). |
| Navigation | 7.0 | Sidebar contextuelle par module (Pilotage/Patrimoine/Énergie/Achat/Admin). Redirect `/` → `/cockpit` élimine le doublon. CommandPalette propre (5 items visibles). |
| Scope / Gouvernance | 7.0 | ScopeSwitcher "Groupe HELIOS · Siege HELIOS Paris" visible dans le header. Scope rappelé partout. Breadcrumbs cohérents. |
| KPI / Calcul | 5.0 | 160 actions/5 sites ABSURDE. Conformité 59 vs 0%. Bill Intel 148 insights/36 factures. Portfolio 3.9M kWh crédible mais actions irréalistes. |
| Facturation / Achat | 7.0 | Bill Intel riche (drawer breakdown Facturé vs Attendu). Achat excellent. Renouvellements : seulement 2 contrats sur 1 site. |
| Workflow / Actionability | 6.0 | "Créer une action" partout, mais 160 actions existantes noient le signal. Pas de guidage "par quoi commencer". |
| Demo credibility | 6.0 | Footer PROMEOS v1.0 ✓. Mais connecteurs "(stub)" visibles, onboarding 0/6, 160 actions, tout rouge en Bill Intel. |
| Architecture visible | 7.5 | Status page propre (v1.0, 6/6 OK). "Endpoints API: -" reste (dash au lieu d'un nombre). Aucun localhost, aucun port visible. |
| Wording / Microcopy | 7.0 | Bon effort FR. Labels cohérents (Actions & Suivi, Conformité réglementaire, Vue exécutive). "KB locale chargée" warning visible sur Mémobox. |
| Responsive / Densité | 6.5 | Cockpit très dense (scroll 3+ écrans). Renouvellements très vide (2 lignes). Activation montre 1 site au lieu de 5. |
| Product Story | 7.0 | Promesse claire : cockpit opérationnel B2B énergie France. Modules forts (Achat, Conso, Usages). Dilué par le bruit des volumes. |

---

## 3. Top problèmes critiques

| ID | Problème | Zone | Pourquoi c'est grave | P | Effort | Type |
|----|----------|------|---------------------|---|--------|------|
| C1 | 160 actions / 734k EUR pour 5 sites | Actions | Un energy manager sait que 5 sites ≠ 160 actions. Absurde. Moteur sync_actions génère automatiquement. | P0 | M | Data / Moteur |
| C2 | Onboarding "Progression: 0/6" après seed complet | Onboarding | Code fixé mais DB pas re-seedée. Premier contact raté. | P0 | XS | Seed / Deploy |
| C3 | Connecteurs "(stub - clé requise)" affichés | Connectors | Code fixé mais serveur pas redémarré. Technique visible. | P0 | XS | Deploy |
| C4 | Bill Intel : 148 insights / 36 factures (tout rouge/orange) | Facturation | Trop d'anomalies = détection non crédible. "Si tout est anomalie, rien n'est anomalie." | P0 | M | Data / Calibrage |
| C5 | Conformité 59/100 vs "0%" conforme global | Conformité | Deux chiffres contradictoires sur la même page | P1 | S | KPI / Logique |
| C6 | Renouvellements : 2 contrats / 1 seul site | Achat | 4 sites sans contrat = page vide pour la majorité | P1 | M | Data / Seed |
| C7 | Activation : "Sites (1)" au lieu de 5 | Activation | Page annonce 5/5 actives mais ne montre qu'1 site | P1 | S | Logique / Filtre |
| C8 | "Endpoints API: -" sur Status | Status | Dash visible = information manquante | P2 | XS | Technique |
| C9 | Mémobox "0 items" + "KB locale chargée" warning | KB | Page vide + warning technique visible | P2 | S | Data / UX |
| C10 | Energy Copilot : page vide accessible via URL | Copilot | Retiré de Ctrl+K mais route existe. Si prospect tape l'URL → page vide. | P2 | XS | Route |
| C11 | Cockpit : page extrêmement longue (3+ écrans scroll) | Cockpit | Prospect perd le fil. Pas de sections collapsibles. | P2 | M | UX / Densité |
| C12 | Portfolio conso 3.9M kWh incohérent vs Explorer 527 MWh | Conso | Explorer = 1 site, Portfolio = 5 sites. Pas de note explicative → confusion | P2 | XS | UX / Contexte |

---

## 4. Audit détaillé par zone

### Cockpit (Vue exécutive)

- **Fonctionne** : Hiérarchie claire, briefing contextuel "SPÄ excédentaire", score 59/100 avec confiance, KPIs avec tendances, lien vers diagnostic.
- **Faible** : Page TRÈS longue (3+ scroll screens). Mini-KPI "4 sites / 100% / 0 alertes" en bas contredit "5 sites" ailleurs. Section "Activation des données 5/7 étapes" visible — à quoi correspond le 7 ?
- **Trompeur** : "0 alertes" en bas vs "5 critiques" dans notifications.
- **Prospect** : Premier écran bon. Perd le fil au 2e scroll.

### Patrimoine (Sites & Bâtiments)

- **Fonctionne** : 5 sites visibles, heatmap couleur par risque, carte MapLibre, drawer site détaillé avec onglets (Résumé/Anomalies/Compteurs/Actions).
- **Faible** : Drawer montre "Risque: —", "OPERAT: —", "Anomalies: 0". Beaucoup de "—".
- **Trompeur** : Risque global "206 k€" sans explication de calcul.
- **Prospect** : Carte et heatmap impressionnent. Drawer trop vide.

### Consommations (Explorateur)

- **FORCE** : 527 MWh, 84 148 EUR, 119.81 €/MWh, 27 t CO2, 240 kW. Graphe mensuel clair. Filtres Élec/Gaz/Eau/PV/GD/FRD. Mode Expert visible.
- **Point fort démo absolu.** Fait "produit mature".

### Consommations (Portefeuille)

- **Fonctionne** : 3 940 749 kWh total, 267 971 EUR, 224 229 kg CO2, 5/5 sites. Rankings visibles.
- **Faible** : Chiffres très différents de l'Explorateur (portfolio = 5 sites vs explorer = 1 site). Pas de note explicative.

### Facturation (Bill Intel)

- **Fonctionne** : Structure riche, 26 factures, drawer "Comprendre l'écart" avec breakdown 5 composantes.
- **GRAVE** : 148 insights = ~4 anomalies par facture. Quasi tout rouge/orange. Écart total 173 627 EUR.
- **Prospect** : "Si votre moteur détecte des anomalies partout, c'est le moteur qui est mal calibré."

### Facturation (Timeline)

- **Fonctionne** : Comparaison mensuelle, barre de couverture, périodes manquantes listées avec export CSV/PDF.
- **Faible** : "85% des mois ont facture" — 15% manquant = problème de seed, pas de contexte.

### Achat énergie

- **MEILLEUR MODULE** : 4 scénarios (Prix Fixe 0.0750/Indexé 0.0720/Spot 0.0865/Tarif Heures Solaires 0.0642). Score risque 42/100. Recommandation "Tarif Heures Solaires".
- **Force** : CTA "Créer une action", "Voir les actions", "Exporter Note Décision.pdf". Hypothèses visibles. Barre tolérance au risque.
- **Faible** : "Post-ARENH v3.0.0" — trop technique pour un prospect.

### Assistant Achat

- **Fonctionne** : Wizard 8 étapes. 5 sites listés avec MWh/an et surface. "Mode demo" checkbox.
- **Faible** : Étape 1/8 = sélection périmètre. 7 étapes restantes = long. Pas de progression estimée.

### Renouvellements contrats

- **Fonctionne** : Radar d'échéances, filtres 30j/60j/90j/180j/1an. Badge "Tertiaire Privé 30%".
- **GRAVE** : Seulement 2 contrats pour Siege HELIOS Paris (Engie + EDF). 4 autres sites sans contrat. Page quasi-vide.
- **Prospect** : "Votre radar de renouvellement ne couvre qu'1 site sur 5 ?"

### Actions & Suivi

- **Fonctionne** : Table structurée, colonnes (Type, Site, Priorité, Impact EUR, Gain, Statut). Filtres.
- **GRAVE** : 153 actions affichées. "À prioriser: 6, En cours: 1". 734 528 EUR total. Absurde pour 5 sites.
- **Prospect** : "160 actions ? Vous les avez générées automatiquement."

### Conformité réglementaire

- **Fonctionne** : Score 59/100 avec barre visuelle, confiance badge, piliers BACS/Tertiaire/APER. "1 obligation en retard" avec détails.
- **GRAVE** : "0%" conforme global visible en bas de page. Contradictoire avec le 59/100.
- **Faible** : "4 à qualifier" — que signifie "à qualifier" ? Pas clair.

### Conformité Tertiaire / OPERAT

- **Fonctionne** : 3 EFA évaluées, entités fonctionnelles listées proprement. Noms réalistes (DPE Bureau Regional Lyon, DPE Hotel HELIOS Nice, etc.).
- **Faible** : "0 sites éligibles" mais 3 EFA évaluées = incohérent. Bouton "Créer l'EFA" visible.
- **Amélioration V2** : Plus de "DPE loi check" ou "Test EJE VR3" ✓ (nettoyé via re-seed).

### Notifications / Alertes

- **Fonctionne** : 10 alertes, 4 nouvelles, 5 critiques, 2 avertissements. Table propre avec badges source/statut.
- **Amélioration V2** : Diversité des sources ✓ (billing + consumption + compliance + action_hub).
- **Bon** : Volume crédible (10 pour 5 sites).

### Diagnostic

- **Fonctionne** : 8 alertes, 251 k€ impact, 72 162 kg CO2. Indicateurs par site avec type et message.
- **Faible** : Beaucoup de "Données détectées" de type "coverage_gap" pour tous les sites = même pattern répété.

### Monitoring / Performance

- **Fonctionne** : 4 155 EUR/an économies, "Non détecté" pour gaspillage, OK pour dépassement, 72% solaire.
- **Faible** : "Non détecté" sans explication = ambigu (pas de données ou pas de problème ?).
- **Force** : Plan d'action avec estimation de gain.

### Usages & Horaires

- **FORCE** : Score comportement 99, heatmap 7×24 colorée (rouge = pics), profil journalier.
- **Faible** : Score "99" sans échelle ni explication = opaque. "0%" week-end et "0%" hors-horaires = suspects.

### Admin (Utilisateurs)

- **Fonctionne** : 4 utilisateurs, 4 rôles distincts, emails crédibles. Scopes "O:1". "3 Sans connexion".
- **Amélioration V2** : 4 users au lieu de 1 ✓.
- **Faible** : "Sans connexion" pour 3 users → normal en demo mais visible.

### Onboarding (Démarrage)

- **CASSÉ** : "Progression: 0/6, 0%". Tous les steps montrent "Marquer terminé". Bouton "Détection auto" ne détecte rien.
- **Cause** : Code fixé dans orchestrator mais DB pas re-seedée après commit.
- **Impact** : Premier contact catastrophique. Si un prospect arrive ici, il voit "rien n'est fait".

### Connectors (Connexions)

- **CASSÉ (visuellement)** : "Meteo-France API (stub - clé requise)", "Enedis Open Data (stub)", "Enedis Data Connect OAuth (stub - clés requises)".
- **Cause** : Code Python fixé, commit pushé, mais serveur backend tourne sur l'ancien code. Restart nécessaire.
- **Force** : Section "À propos des Connecteurs" propre, descriptions API publique/OAuth claires.

### Activation

- **Fonctionne** : "5/5 briques actives" sans banner contradictoire ✓.
- **Faible** : "Sites (1)" = seul Siege HELIOS Paris visible. 4 autres sites non affichés. Filtrage ou bug.
- **Amélioration V2** : Plus de contradiction "5/5 actives" + "Données incomplètes" ✓.

### Status (Système)

- **Fonctionne** : "Statut PROMEOS", "Backend connecté, Version 1.0.0", 6/6 checks OK. Footer "PROMEOS v1.0".
- **Amélioration V2** : Plus de "PROMEOS POC | FastAPI + React + SQLite | 427 tests" ✓.
- **Faible** : "Endpoints API: -" = dash visible.

### Mémobox (KB)

- **Faible** : "0 items", warning "KB locale chargée — Le service Mémobox n'est pas disponible", page vide.
- **Amélioration V2** : Footer dynamique "0 items de connaissance" au lieu de "457 items ingérés" ✓.
- **Problème** : Page accessible mais vide = inutile en démo.

### Segmentation B2B

- **Fonctionne** : Profil "Tertiaire Privé 30%", questionnaire 8 questions, UX propre.
- **Faible** : 8/8 réponses = 30% seulement ? Pas clair. "Répondez aux questions pour affiner votre profil" mais toutes sont répondues.

### Command Palette (Ctrl+K)

- **Fonctionne** : 5 items principaux visibles (Cockpit, Actions & Suivi, Notifications, Sites & Bâtiments, Conformité). Recherche rapide.
- **Amélioration V2** : Energy Copilot et Tableau de bord retirés ✓.

### Sidebar

- **Fonctionne** : Contextuelle par module. Icônes claires. Badge "7" sur Actions & Suivi, badge "10" sur Performance.
- **Faible** : Badge "10" sur Performance sans contexte (10 quoi ?).

### Header

- **Fonctionne** : Breadcrumbs cohérents. ScopeSwitcher visible. Toggle Expert. Recherche Ctrl+K.
- **Bon** : Utilisateur "Promeos Admin / DG / Owner" visible.

---

## 5. Contradictions & pertes de confiance

| Type | Détail |
|------|--------|
| Chiffres contradictoires | Conformité 59/100 vs "0% conforme global" sur la même page |
| Volumes absurdes | 160 actions / 734k EUR pour 5 sites (moteur sync génère automatiquement) |
| Bill Intel calibrage | 148 insights / 36 factures = tout est anomalie |
| Cockpit mini-KPI | "4 sites" en bas vs "5 sites" dans patrimoine |
| Cockpit alertes | "0 alertes" mini-KPI vs "5 critiques" notifications |
| Activation filtre | "5/5 briques actives" mais "Sites (1)" dans le tableau |
| Renouvellements vide | 2 contrats / 1 site. 4 sites sans contrat. |
| Onboarding 0/6 | Code fixé mais pas déployé → seed DB obsolète |
| Connecteurs stub | Code fixé mais serveur pas redémarré |
| Mémobox vide | "0 items" + warning technique "KB locale chargée" |
| Score opaque | Comportement "99" (usages horaires) sans échelle |
| Endpoints API | "Endpoints API: -" (dash) sur page Status |
| Performance badge | "10" en sidebar sans contexte |

---

## 6. Audit customer journey / workflow

### Scénario 1 — Prospect / démo commerciale

| Étape | Verdict |
|-------|---------|
| Cockpit | Bon premier impact. Briefing, score, KPIs. Mais scroll très long. |
| Patrimoine | Carte MapLibre impressionne. Heatmap sites claire. Drawer un peu vide ("—"). |
| Facturation | **CHOC** : tout est rouge/orange. 148 insights = "votre moteur détecte n'importe quoi". |
| Achat | **EXCELLENT** : 4 scénarios, recommandation, export PDF. Meilleur module. |
| Actions | **CHOC** : 160 actions. "C'est quoi ces chiffres ?" |
| Verdict global | "Modules forts (Achat, Conso) mais volumes absurdes = pas crédible en l'état." |

### Scénario 2 — DG multi-sites

| Étape | Verdict |
|-------|---------|
| ScopeSwitcher | Fonctionne. Groupe HELIOS visible. |
| Cockpit | Score 59, briefing clair. Mais "où est la synthèse en 30 secondes ?" — trop long. |
| Actions | 160 actions / 734k = "C'est absurde, je gère 5 bâtiments pas 160 chantiers." |
| Achat | 4 scénarios + recommandation = "ça c'est utile". |

### Scénario 3 — Energy Manager

| Étape | Verdict |
|-------|---------|
| Recherche site | Ctrl+K → propre, 5 items. Pas de recherche par nom de site directement. |
| Explorer conso | **BON** : 527 MWh, graphe, filtres. Sait où il est (scope rappelé). |
| Diagnostic | 8 alertes, impacts chiffrés. Bon. |
| Créer action | CTA "Créer une action" disponible dans Achat, Patrimoine, Conformité. Bon. |
| Scope | Rappelé partout via ScopeSwitcher. OK. |

### Scénario 4 — Expert

| Étape | Verdict |
|-------|---------|
| Mode Expert | Toggle visible en header. Fonctionne. |
| Usages & Horaires | Heatmap 7×24 impressionnante. Score 99 opaque mais visuel expert. |
| Command Palette | Propre. Plus de pages mortes. Expert toggle fonctionne via Ctrl+K. |
| Bill Intel drawer | Breakdown 5 composantes, détail technique. Bon niveau expert. |

### Scénario 5 — Admin / gouvernance

| Étape | Verdict |
|-------|---------|
| Utilisateurs | 4 users, 4 rôles, emails réalistes. Propre. |
| Onboarding | **CASSÉ** : 0/6. Premier contact raté. |
| Connectors | "(stub)" visible = technique visible. |
| Status | v1.0, 6/6 OK. Propre sauf "Endpoints API: -". |

---

## 7. Audit spécial chiffres / KPI / calcul

| Question | Réponse |
|----------|---------|
| **KPI fiables** | Conso (527 MWh, 84k EUR) dans l'Explorateur ; Portfolio (3.9M kWh, 268k EUR, 224k kg CO2) ; Achat (4 scénarios chiffrés). |
| **KPI opaques** | Score conformité 59/100 (quelle méthode ?) ; Score comportement 99 (quelle échelle ?) ; Confiance badges (sans tooltip) ; Score risque achat 42/100. |
| **KPI contradictoires** | 59/100 conformité vs "0% conforme global" ; "4 sites" cockpit vs "5 sites" patrimoine ; "0 alertes" cockpit vs "5 critiques" notifications. |
| **Chiffres mal visibles** | Mini-KPI cockpit en bas de page (4 sites, 100%, 0) = noyés dans le scroll. |
| **Chiffres sans contexte** | 3.9M kWh sans benchmark secteur ; 160 actions sans ratio "/site" ; 734k EUR sans temporalité ; "10" badge sidebar. |
| **Chiffres suspects** | 160 actions/5 sites = 32 actions/site = absurde ; 148 insights/36 factures = 4.1 anomalies/facture = suspect ; 734k EUR savings = irréaliste pour 5 sites tertiaires. |
| **Calculs non démontrables** | Shadow billing breakdown (5 composantes) — vérifiable par un expert ELEC ? TURPE, accise, TVA = paramétrable ? |

---

## 8. Audit spécial démo / quasi-production

### Fait encore POC
- Connecteurs "(stub)" visibles (serveur pas redémarré)
- Onboarding 0/6 (DB pas re-seedée)
- 160 actions / 734k EUR = volumes moteur non calibrés
- Bill Intel tout rouge (148 insights / 36 factures)
- Mémobox vide + warning "KB locale chargée"
- "Endpoints API: -" sur Status
- Renouvellements : 2 contrats / 1 site
- Energy Copilot accessible via URL directe (page vide)
- "0% conforme" vs 59/100
- Activation "Sites (1)" au lieu de 5

### Fait produit mature
- **Status** : PROMEOS v1.0, 6/6 checks, plus de "POC | SQLite" ✓
- **Explorateur conso** : KPI, graphe, filtres, mode expert ✓
- **Achat énergie** : 4 scénarios, recommandation, export PDF ✓
- **Usages horaires** : Heatmap 7×24, profil, score ✓
- **ScopeSwitcher** : Breadcrumbs, scope rappelé partout ✓
- **Admin users** : 4 utilisateurs, 4 rôles crédibles ✓
- **Notifications** : 10 alertes, 4 sources, volumes réalistes ✓
- **Command Palette** : Propre, pas de pages mortes ✓
- **Patrimoine carte** : MapLibre interactif, heatmap sites ✓
- **Sidebar contextuelle** : Module-specific, icônes cohérentes ✓

### Ce qui bloque une vraie démo client
1. Redémarrer le serveur backend (connecteurs stub → descriptions propres)
2. Re-seeder la DB (onboarding 0/6 → 6/6)
3. Calibrer sync_actions (160 → 25-35 actions max)
4. Calibrer Bill Intel (148 insights → 30% anomalies max = ~10 insights)
5. Fixer conformité 0% vs 59

### Ce qui bloque une présentation investisseur
1. Volumes absurdes = "c'est du bruit, pas du signal"
2. Cockpit trop long sans synthèse rapide
3. Pas de "moment wow" guidé
4. Trop de pages (27) sans priorité

---

## 9. Recommandations classées

### P0 — Avant toute démo (BLOQUANT)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | **Restart backend** + re-seed DB (`--reset`) | Élimine stub + onboarding 0/6 | XS (5 min) |
| 2 | **Calibrer sync_actions** : cap à 25-35 actions max pour 5 sites | Crédibilité volumes | M (2h) |
| 3 | **Calibrer Bill Intel** : réduire sensibilité shadow billing → max 30% anomalies | Crédibilité facturation | M (2h) |
| 4 | **Conformité** : fixer "0% conforme" vs 59/100 — supprimer ou aligner le 0% | Cohérence KPI | S (1h) |

### P1 — Sprint suivant

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 5 | Seed contrats pour tous les sites (pas juste Siege Paris) | Renouvellements crédible | M (2h) |
| 6 | Activation : afficher les 5 sites (pas seulement 1) | Cohérence | S (30min) |
| 7 | Cockpit : sections collapsibles ou "résumé 30 secondes" en haut | UX exécutive | M (3h) |
| 8 | "Endpoints API: -" → afficher le vrai nombre ou masquer | Qualité | XS (15min) |
| 9 | Score comportement 99 + conformité 59 : ajouter tooltip méthode | Transparence | S (1h) |
| 10 | Performance badge "10" : ajouter tooltip | UX | XS (15min) |

### P2 — Ensuite

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 11 | Mémobox : seeder des items KB ou masquer la page | Crédibilité | M |
| 12 | Supprimer la route `/energy-copilot` (page vide) | Propreté | XS |
| 13 | Patrimoine drawer : remplacer "—" par "Non évalué" | Micro-UX | S |
| 14 | Cockpit mini-KPI : aligner "4 sites" → "5 sites" | Cohérence | XS |
| 15 | Achat : retirer "Post-ARENH v3.0.0" du sous-titre | Simplicité | XS |

### Surveiller seulement
- Portfolio vs Explorer kWh (contexte différent = normal, mais pas expliqué)
- "Sans connexion" pour 3 users admin (normal en demo)
- Segmentation "30%" malgré 8/8 réponses (logique interne OK ?)

---

## 10. Plan priorisé

| # | Action | Impact | Effort | Pourquoi maintenant |
|---|--------|--------|--------|---------------------|
| 1 | Restart backend + re-seed `--reset` | CRITIQUE | 5 min | Élimine stub + onboarding. Zéro code. |
| 2 | Cap sync_actions à 25-35 max | CRITIQUE | 2h | 160 actions = kill shot #1 prospect |
| 3 | Calibrer shadow billing (30% anomalies max) | CRITIQUE | 2h | Bill Intel tout rouge = kill shot #2 |
| 4 | Fixer conformité 0% vs 59 | MAJEUR | 1h | Contradiction visible en 1 clic |
| 5 | Seed contrats pour 5 sites | MAJEUR | 2h | Renouvellements vide = suspect |
| 6 | Activation : afficher 5 sites | MINEUR | 30min | Incohérence visible |
| 7 | Cockpit résumé rapide | UX | 3h | DG perd le fil au scroll |
| 8 | Tooltips scores + badges | TRANSPARENCE | 1h | Scores opaques = méfiance |
| 9 | Mémobox seed ou masquer | CRÉDIBILITÉ | 1h | Page vide = inutile |
| 10 | Cleanup routes mortes | PROPRETÉ | 30min | Energy Copilot, fallbacks |

---

## 11. Verdict final

**PROMEOS est-il réellement crédible aujourd'hui ?**
Non, pas en l'état. Les corrections P0/P1 ont éliminé les fuites techniques les plus grossières (footer POC, 1 user, onboarding dans le code). Mais l'exécution est incomplète — le serveur tourne sur l'ancien code — et le problème SYSTÉMIQUE reste : les moteurs automatiques (sync_actions, shadow billing) génèrent des volumes absurdes qui détruisent la crédibilité.

**Qu'est-ce qui empêche encore un effet "top world" ?**
1. Le bruit : trop d'actions, trop d'anomalies, trop de pages, trop de scroll.
2. L'absence de storytelling : pas de "moment wow" guidé, pas de parcours prospect.
3. Les contradictions chiffrées : 59 vs 0%, 160 actions/5 sites, tout rouge Bill Intel.

**Qu'est-ce qui doit être corrigé AVANT toute nouvelle feature ?**
1. Restart + re-seed (5 min)
2. Cap sync_actions (2h)
3. Calibrer shadow billing (2h)
4. Fixer conformité 0% (1h)
= **~6h de travail concentré**

**Qu'est-ce qui doit être gelé car déjà assez bon ?**
- Explorateur consommation — ne toucher à rien
- Achat énergie + Scénarios — gelé
- Usages & Horaires (Heatmap) — gelé
- ScopeSwitcher + Breadcrumbs — gelé
- MapLibre patrimoine — gelé
- Status page — gelé (v1.0 ✓)
- Admin users — gelé (4 users ✓)
- Notifications — gelé (10 alertes ✓)
- Command Palette — gelé

**Si on devait montrer PROMEOS demain à un prospect exigeant, qu'est-ce qui ferait peur ?**
1. "160 actions pour 5 sites ? C'est du bruit automatique."
2. "Toutes vos factures sont en anomalie ? Votre moteur est cassé."
3. "59% conforme mais 0% conforme ? Vous ne savez pas compter."
4. "Votre onboarding dit 0/6 alors que tout est configuré."
5. "Vos connecteurs disent stub."

**Temps pour passer de 71 à 85/100** : ~8-10h de travail concentré sur les 6 premières actions du plan.
