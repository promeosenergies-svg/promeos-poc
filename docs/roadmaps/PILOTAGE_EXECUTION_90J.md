# PILOTAGE D'EXÉCUTION PROMEOS — 90 JOURS

> **Date** : 11 mars 2026
> **Rôle** : Chief of Staff Produit + PMO d'exécution + QA stratégique
> **Version** : 2.1 — Couche de pilotage
> **Réf.** : Se lit en complément de `PLAN_EXECUTION_90J.md` (v2.0)
> **Statut** : BASELINE FIGÉE

---

## 1. SYNTHÈSE EXÉCUTIVE

### Plan confirmé — version finale

Le plan 90 jours est validé et figé. 4 paris, 12 semaines, 3 KPIs, 3 gates. Ce document ajoute la couche de pilotage qui manquait : baseline officielle, buffer réaliste, cadre benchmark défendable, tableau de bord hebdo, brief d'entrée pour l'audit Patrimoine.

### Message central

> **On ne rouvre plus le scope.**
> 4 paris : Coffre → PDF → Notifications → Benchmark.
> Le buffer vit dans S4, S6, S9, S10. Pas ailleurs.
> Le benchmark V0 utilise les données ADEME/CEREN publiques avec disclaimer explicite.
> Chaque vendredi : 1 tableau de bord, 1 preuve, 1 décision.
> L'audit Patrimoine est briefé, pas lancé.

---

## 2. DÉCISIONS

### FAITS

**Ce qui est validé dans le plan actuel :**
- Les 4 paris sont les bons, dans le bon ordre, avec les bonnes dépendances
- Les gates G1/G2/G3 ont des critères mesurables et des règles de blocage
- Les 3 KPIs (preuves/obligation, PDF générés, actions compliance) sont les bons signaux
- Le plan semaine par semaine est réaliste pour 1.5 ETP
- APER est correctement sorti du chemin critique

**Ce qui devait être renforcé :**
- Pas de baseline officielle figée → risque de scope creep silencieux
- Pas de buffer explicite → le plan S4-S10 est tendu à 100% de capacité
- Pas de source benchmark verrouillée → risque de "fake precision" en démo
- Pas de tableau de bord unique → review vendredi sans cockpit
- Pas de brief patrimoine → risque de lancer l'audit sans cadre

### HYPOTHÈSES

**Où le risque d'exécution existe encore :**
- **S4 (PDF backend)** : WeasyPrint sur Windows est un risque technique réel. Le spike S3 doit trancher.
- **S6 (GATE G1)** : 6 semaines pour coffre + PDF + début notifications est serré. Si S4 dérape, G1 glisse.
- **S7-S8 (Benchmark)** : La qualité des données ADEME conditionne la crédibilité. Si les données sont trop agrégées, le widget perd son impact.
- **S9 (Intégration)** : 4 features cross-connected la même semaine. C'est le point de fragilité #1.

### DÉCISIONS

| Décision | Statut |
|----------|--------|
| Baseline figée — aucun ajout de scope avant G2 | **VALIDÉ** |
| Buffer 12% ajouté sur S4-S10 (4 demi-journées) | **VALIDÉ** |
| Source benchmark : ADEME/CEREN + disclaimer obligatoire | **VALIDÉ** |
| Tableau de bord unique pour review vendredi | **VALIDÉ** |
| Brief audit Patrimoine prêt, lancement post-G2 | **VALIDÉ** |

---

## 3. BASELINE OFFICIELLE 90 JOURS

### SCOPE IN — Ce qu'on commit

| # | Engagement | Livrable tangible | Gate |
|---|-----------|-------------------|------|
| 1 | Coffre de preuves persisté (backend + frontend) | API REST proofs, ProofUpload, seed démo, hash SHA-256 | G1 |
| 2 | Dossier PDF comité (backend + frontend) | pdf_generator.py, endpoint PDF, bouton download, template complet | G1 |
| 3 | Notifications échéances (engine + UI + digest) | notification_engine.py, cloche AppShell, email digest preview | G2 |
| 4 | Benchmark sectoriel V0 (données + API + widget) | BenchmarkRef seedé, endpoint benchmark, widget "vs médiane" | G2 |
| 5 | Intégration cross-features | Parcours démo 15 min fluide bout en bout | G2 |
| 6 | Stabilisation + tests | CI 100% green, zéro crash démo | G2 |
| 7 | Projection 2030 V0 (si G2 atteint) | Sparkline trajectoire dans obligation DT | G3 prep |
| 8 | Lien conformité → conso (si G2 atteint) | Widget kWh/m²/an + lien vers /consommations | G3 prep |

### SCOPE OUT — Ce qu'on ne fait PAS avant G2

| Initiative | Pourquoi c'est dehors | Quand au plus tôt |
|-----------|----------------------|-------------------|
| APER enrichi (calcul kWc) | Hors chemin critique, 0 demande prospect | Quick win S12 ou H2 |
| Projection 2030 complète | Dépend du benchmark | S11 (post-G2) |
| Simulation "si j'agis" | Dépend benchmark + projection | H3 (mois 4-5) |
| Lien conformité → facture | Shadow billing existe, UI peut attendre | H2-H3 |
| Workflow multi-acteurs | 0 client avec 2 rôles actifs | H3-H4 |
| Connecteur OPERAT auto | API OPERAT indisponible | H3 |
| Rapports périodiques auto | Dépend du PDF engine | H3 |
| Veille réglementaire push | Échéances connues suffisent | H3 |
| Multi-tenant SaaS | Pas avant 5 prospects qualifiés | H4 |
| API publique | Pas avant 1 intégrateur identifié | H4 |

### RÈGLE ANTI-SCOPE-CREEP

> **Toute idée nouvelle est ajoutée à la liste "scope out" avec une date "au plus tôt".**
> **Aucune exception avant G1.**
> **Exception possible entre G1 et G2 : uniquement si effort < 0.5j ET lié à un des 4 paris.**

### CHANGELOG : Roadmap large → Plan exécutable

| Élément | Roadmap v1.0 | Plan v2.1 | Raison |
|---------|-------------|-----------|--------|
| APER enrichi | H1 (0-30j) | Quick win S12 ou H2 | Hors chemin critique, 0 lock-in |
| Benchmark | H2 (31-90j) | H1 S7-S8 (avancé) | Argument DG #1 en démo |
| Lien conformité→conso | H2 (31-90j) | S11 (si G2 ok) | Moins urgent que benchmark |
| Lien conformité→facture | H2 (31-90j) | H2-H3 | Repoussé, shadow billing suffit |
| Workflow multi-acteurs | H2 (31-90j) | H3-H4 | Aucun usage réel |
| KPIs | 7 KPIs | 3 KPIs | Focus |
| Gates | Aucune | G1/G2/G3 mesurables | Pilotage |
| Granularité | "0-30 jours" | Semaine par semaine | Exécution réelle |
| Buffer | Aucun | 12% sur S4-S10 | Réalisme |

---

## 4. CALENDRIER 12 SEMAINES AVEC BUFFER

### Principe de buffer

- **Budget buffer total** : 4 demi-journées réparties sur S4-S10 (~12% de la capacité)
- **Où il vit** : intégré dans les sprints S4, S6, S9, S10 (les semaines à risque)
- **Comment il se consomme** : bug fixing, retard sprint précédent, edge case technique
- **Comment on le protège** : le buffer n'est JAMAIS utilisé pour ajouter du scope

### Calendrier détaillé

| Sem. | Dates | Pari | Objectif | Livrables | Buffer | Owner | Preuve vendredi |
|------|-------|------|----------|-----------|--------|-------|-----------------|
| **S1** | 11-14 mars | Coffre | Backend API proofs | modèle ProofFile, API REST (POST/GET/DELETE), stockage filesystem, validation type/taille, tests pytest | — | Lead dev | `curl` upload → retrieve → delete OK |
| **S2** | 17-21 mars | Coffre | Frontend upload | ProofUpload.jsx (drag&drop), proofService.js, remplacement useState → API, PreuvesTab connecté | — | Lead dev | Upload PDF → F5 → toujours là |
| **S3** | 24-28 mars | Coffre + PDF spike | Polish + choix tech PDF | Hash SHA-256, seed ProofFile démo, compteurs preuves, spike WeasyPrint vs Playwright PDF | — | Lead dev | Seed preuves visibles + 1 page PDF générée |
| **S4** | 31 mars - 4 avr | PDF | Template + engine backend | pdf_generator.py, template HTML/CSS, endpoint /dossier/pdf, contenu complet | **0.5j** bug fix coffre | Lead dev | `curl GET .../pdf` → PDF lisible |
| **S5** | 7-11 avril | PDF + Notif | Bouton PDF + modèle notif | Bouton download ConformitePage, modèle Notification, routes notifications | — | Lead dev | Clic → PDF téléchargé. API notif retourne [] |
| **S6** | 14-18 avril | Notif | Engine + UI cloche | notification_engine.py, trigger endpoint, cloche AppShell, badge, panneau, mark as read | **0.5j** stabilisation G1 | Lead dev | Trigger → 5+ notifs. Cloche badge. **GATE G1** |
| **S7** | 21-25 avril | Notif + Bench | Email digest + données | email_digest.py (preview HTML), modèle BenchmarkRef, seed ADEME/CEREN 30+ entrées | — | Lead dev | Email preview lisible + benchmark seedé |
| **S8** | 28 avr - 2 mai | Bench | API + widget frontend | Endpoint benchmark, matching auto site→ref, widget barre P25/médiane/P75/site, intégration score header | — | Lead dev | Widget "vs médiane" visible en démo |
| **S9** | 5-9 mai | Intégration | Tout ensemble | Benchmark dans PDF, notifications dans seed, parcours démo 15 min bout en bout | **1j** bug fixing intégration | Lead dev | Screencast parcours démo complet |
| **S10** | 12-16 mai | Stabilisation | Tests + polish | Tests complets (proofs, pdf, notif, benchmark), source guards frontend, polish UX, seed optimal | **1j** edge cases + polish | Lead dev | CI 100% green. 0 crash démo. **GATE G2** |
| **S11** | 19-23 mai | Projection | Trajectoire 2030 + lien conso | projection_trajectory.py, sparkline DT, lien "Voir conso" → /consommations, widget kWh/m²/an | — | Lead dev | Sparkline visible + lien fonctionnel |
| **S12** | 26-30 mai | Démo ready | Script démo + rétro | Script démo 15 min affiné, guide interne, APER QW si temps, rétrospective 90j | — | Lead dev + Product | Démo interne filmée. **GATE G3 prep** |

### Résumé buffer

| Semaine | Buffer | Usage prévu |
|---------|--------|-------------|
| S4 | 0.5j | Bug fix coffre preuves (upload edge cases, types invalides) |
| S6 | 0.5j | Stabilisation pré-G1 (coffre + PDF + notifications base) |
| S9 | 1.0j | Bug fixing intégration cross-features (4 systèmes ensemble) |
| S10 | 1.0j | Edge cases tests + polish UX pré-G2 |
| **Total** | **3.0j** | **~12% de la capacité S4-S10 (25j ouvrés)** |

### Règle en cas de dérapage

| Situation | Action |
|-----------|--------|
| Sprint en retard ≤ 1j | Consommer le buffer de la semaine suivante |
| Sprint en retard > 2j | Couper le livrable le moins critique du sprint |
| S6 en retard → G1 menacée | Reporter G1 à fin S7. NE PAS commencer benchmark. |
| S10 en retard → G2 menacée | Reporter G2 à fin S11. S11-S12 deviennent stabilisation. |
| Buffer épuisé avant S10 | Alerte rouge → review scope avec Product Owner |

---

## 5. CADRE BENCHMARK V0

### Source principale

| Élément | Décision |
|---------|----------|
| **Source autorisée** | **ADEME — Chiffres clés du bâtiment** (édition 2024) + **Base DPE/CEREN** agrégée |
| **Granularité** | Consommation finale kWh/m²/an par usage × zone climatique × tranche de surface |
| **Année de référence** | 2022 (dernières données consolidées ADEME) |
| **Format** | Médiane, P25 (performant), P75 (énergivore) |
| **Licence** | Données publiques, licence ouverte Etalab — utilisable commercialement |

### Hiérarchie de fallback

| Niveau | Source | Granularité | Fiabilité | Quand l'utiliser |
|--------|--------|-------------|-----------|-----------------|
| **1. Idéal** | ADEME/CEREN par usage × zone × tranche surface | Usage + zone H1/H2/H3 + surface <1000/1000-5000/>5000 | Haute | Match exact trouvé |
| **2. Fallback A** | ADEME/CEREN par usage × zone (sans tranche surface) | Usage + zone, toutes surfaces confondues | Moyenne | Pas de donnée pour la tranche de surface |
| **3. Fallback B** | ADEME/CEREN par usage seul (moyenne nationale) | Usage uniquement, toutes zones et surfaces | Faible | Pas de donnée pour la zone climatique |
| **4. Pas d'affichage** | — | — | — | Usage inconnu ou non mappable |

### Règles de matching

| Paramètre | Source dans PROMEOS | Mapping |
|-----------|--------------------|---------|
| **Usage** | `site.usage` ou `batiment.usage_principal` | Mapping vers catégories ADEME : Bureau, Enseignement, Commerce, Santé, Logistique, Hôtellerie, Sport, Culture, Mixte |
| **Zone climatique** | `site.zone_climat` (H1/H2/H3) | Direct — les 3 zones DPE standard |
| **Surface** | `site.tertiaire_area_m2` | Tranches : <1000 m², 1000-5000 m², >5000 m² |
| **Conso réelle** | `site.conso_kwh_m2_an` ou calcul (conso totale / surface) | Si absent : widget non affiché |

### Conditions d'affichage

| Condition | Résultat |
|-----------|---------|
| Usage mappable + zone connue + conso réelle disponible | **Afficher** widget complet (P25/médiane/P75/site) |
| Usage mappable + zone connue + conso absente | **Afficher** référentiel seul ("Médiane secteur : X kWh/m²/an") sans positionnement |
| Usage non mappable OU fallback niveau 4 | **Ne pas afficher**. Pas de benchmark vaut mieux qu'un benchmark faux. |
| Fallback B utilisé (moyenne nationale) | **Afficher** avec mention "(moyenne nationale)" |

### Disclaimer UI

> Texte obligatoire sous chaque widget benchmark :

```
Données de référence : ADEME/CEREN {year}, consommation finale tous usages.
Valeurs indicatives par catégorie d'usage. Ne constituent pas un audit énergétique.
```

Si fallback B (moyenne nationale) :
```
Données de référence : ADEME/CEREN {year}, moyenne nationale (zone climatique non spécifiée).
```

### Risques méthodologiques et garde-fous

| Risque | Impact | Garde-fou |
|--------|--------|-----------|
| Données ADEME trop agrégées (pas de tranche surface) | Benchmark peu discriminant | Utiliser fallback A, documenter la limite |
| Données obsolètes (année de réf. 2022 vs site 2026) | Biais temporel | Afficher l'année de référence. Mise à jour annuelle prévue. |
| Usage "mixte" non significatif | Benchmark misleading | Ne pas afficher si usage = Mixte sans ventilation |
| Surface déclarée erronée | Conso/m² fausse → positionnement faux | Alerte si conso/m² < 20 ou > 500 (probable erreur) |
| "Fake precision" : afficher des décimales | Crédibilité entamée | Arrondir à l'entier. Pas de décimale sur kWh/m²/an. |
| Prospect conteste la source | Perte de confiance | Citer la source ADEME dans chaque widget + lien vers publication |

### Seed V0 — Usages prioritaires

| Usage | Zone H1 (Nord) | Zone H2 (Centre) | Zone H3 (Sud) | Source |
|-------|----------------|-------------------|---------------|--------|
| Bureau | 180 / 210 / 260 | 150 / 185 / 230 | 120 / 155 / 200 | ADEME 2024 |
| Enseignement | 130 / 160 / 210 | 110 / 140 / 185 | 90 / 120 / 160 | ADEME 2024 |
| Commerce | 200 / 250 / 320 | 170 / 220 / 290 | 145 / 190 / 250 | ADEME 2024 |
| Santé | 220 / 270 / 340 | 190 / 240 / 310 | 160 / 210 / 275 | ADEME 2024 |
| Hôtellerie | 170 / 220 / 290 | 145 / 195 / 260 | 120 / 170 / 230 | ADEME 2024 |
| Logistique | 80 / 110 / 160 | 70 / 95 / 140 | 55 / 80 / 120 | ADEME 2024 |

> Format : P25 / Médiane / P75 en kWh/m²/an (énergie finale, tous usages confondus)
> Les 4 usages restants (Sport, Culture, Mixte, Industrie légère) seront ajoutés en H2 si nécessaire.

---

## 6. TABLEAU DE BORD D'EXÉCUTION

### 6A. Statut des 4 paris

> **À mettre à jour chaque vendredi.** Valeurs initiales ci-dessous.

| Pari | Owner | Semaines | Statut | Gate | Preuve attendue cette semaine | Risque principal | Prochaine décision |
|------|-------|----------|--------|------|-------------------------------|------------------|--------------------|
| 1. Coffre de preuves | Lead dev | S1–S4 | `NOT STARTED` | G1 | S1 : curl upload → retrieve → delete | Upload multipart FastAPI + gros fichiers | Choix stockage : filesystem vs blob |
| 2. Dossier PDF comité | Lead dev | S3–S6 | `NOT STARTED` | G1 | — (commence S3) | WeasyPrint sur Windows | Choix tech PDF fin S3 (spike) |
| 3. Notifications | Lead dev | S5–S8 | `NOT STARTED` | G2 | — (commence S5) | Volume notifications trop élevé | Stratégie de regroupement S6 |
| 4. Benchmark V0 | Lead dev | S7–S10 | `NOT STARTED` | G2 | — (commence S7) | Données ADEME trop agrégées | Valider seed données S7 |

### 6B. Statut des gates

| Gate | Date cible | Statut | Critères atteints | Critères restants | Bloqueur |
|------|-----------|--------|-------------------|-------------------|----------|
| G1 | Fin S6 (18 avril) | `NOT STARTED` | 0/5 | Upload F5, PDF download, 60% preuves, <3s upload, CI green | — |
| G2 | Fin S10 (16 mai) | `NOT STARTED` | 0/5 | Notifs 100%, email digest, widget benchmark, 5 PDF, démo fluide | G1 |
| G3 prep | Fin S12 (30 mai) | `NOT STARTED` | 0/5 | 3 démos, 3 feedbacks, projection 2030, lien conso, onboarding <10min | G2 |

### 6C. Suivi des 3 KPIs obsessionnels

| KPI | Valeur actuelle | Cible 30j | Cible 90j | Source de donnée | Seed / Démo / Réel |
|-----|----------------|-----------|-----------|-----------------|---------------------|
| Preuves déposées / obligation | **0** (useState, non persisté) | ≥ 0.5 | ≥ 1.0 | `SELECT COUNT(*) FROM proof_files / COUNT(*) FROM obligations` | Seed : compté mais tagué. Réel : seul qui compte. |
| PDF générés | **0** (DossierPrintView = print CSS) | ≥ 3 | ≥ 10 | `SELECT COUNT(*) FROM pdf_generation_logs` | Seed : non applicable. Démo : compté. Réel : seul qui compte. |
| Actions compliance | **10** (seed gen_actions) | ≥ 5 (hors seed) | ≥ 20 (hors seed) | `SELECT COUNT(*) FROM action_items WHERE source_type='COMPLIANCE' AND created_by != 'seed'` | Seed : 10 existantes, non comptées. Réel : créées manuellement. |

### 6D. Template review vendredi

```
REVIEW VENDREDI — Semaine S{n} — {date}

1. PREUVE DE LA SEMAINE
   [ ] Livrable démontré ? OUI / NON
   [ ] Si NON : pourquoi + action corrective

2. PARIS
   Coffre : {statut}
   PDF    : {statut}
   Notif  : {statut}
   Bench  : {statut}

3. GATE
   Prochaine gate : G{n} — {date}
   Critères atteints : {x}/5
   Bloqueur : {description ou "aucun"}

4. KPIs
   Preuves/obligation : {valeur}
   PDF générés        : {valeur}
   Actions compliance : {valeur}

5. BUFFER CONSOMMÉ
   Total utilisé : {x}j / 3.0j
   Reste : {x}j

6. DÉCISION DE LA SEMAINE
   {1 décision claire prise ou "aucune nécessaire"}

7. RISQUE PRINCIPAL SEMAINE PROCHAINE
   {description}
```

---

## 7. BRIEF D'ENTRÉE — AUDIT PATRIMOINE SITES & BÂTIMENTS

### Statut : PRÊT — Lancement post-G2

> Cet audit ne démarre PAS maintenant. Ce brief prépare le cadre pour que l'audit démarre proprement après G2 (mi-mai), sans temps de ramp-up.

### Objectif de l'audit

Évaluer la qualité, la lisibilité et la complétude du modèle patrimoine PROMEOS (Organisation → Portefeuille → Site → Bâtiment → Compteur) en tant que fondation pour toutes les briques métier : conformité, consommation, facturation, achat, actions, preuves.

### Périmètre

| Couche | Ce qu'on audite | Ce qu'on n'audite pas |
|--------|----------------|----------------------|
| Modèle de données | Tables Org, Site, Batiment, compteurs, relations | Performance SQL, indexation |
| API patrimoine | Endpoints CRUD, réponses, complétude | Sécurité, auth (audité séparément) |
| UI patrimoine | Pages Sites & Bâtiments, SiteDetail, Site360 | Pages Conformité, Billing (auditées séparément) |
| Seed démo | Qualité des 5 sites HELIOS | Seed consommation/facturation |
| Hiérarchie | Org → site → bâtiment → compteur | Multi-org, multi-tenant |

### Questions critiques

| # | Question | Pourquoi c'est critique | Comment le vérifier |
|---|----------|------------------------|---------------------|
| 1 | Le modèle site contient-il tous les champs nécessaires au benchmark ? | Le benchmark V0 a besoin de : usage, zone_climat, surface, conso/m² | Vérifier le modèle Site vs les champs utilisés par BenchmarkRef |
| 2 | La hiérarchie org → site → bâtiment → compteur est-elle cohérente ? | Chaque obligation est rattachée à un site. Chaque preuve à une obligation. Si la hiérarchie casse, tout casse. | Requête : obligations sans site, sites sans org, bâtiments orphelins |
| 3 | Le modèle bâtiment porte-t-il les données CVC nécessaires au BACS ? | L'assujettissement BACS dépend de cvc_power_kw. Si c'est sur le site et pas le bâtiment, c'est un problème multi-bâtiment. | Vérifier Batiment.cvc_power_kw vs Site._cvc_kw |
| 4 | Les surfaces sont-elles fiables et cohérentes ? | tertiaire_area_m2, parking_area_m2, roof_area_m2 conditionnent DT, APER, benchmark. | Vérifier : somme surfaces bâtiments ≈ surface site |
| 5 | L'UI patrimoine est-elle navigable en < 3 clics vers le détail site ? | Un prospect en démo doit accéder rapidement à un site pour voir ses obligations. | Test parcours : accueil → site → obligations |
| 6 | Le seed démo est-il crédible pour 5 usages différents ? | Les 5 sites HELIOS doivent représenter 5 usages distincts (bureau, école, commerce...) pour montrer la couverture. | Vérifier les usages des 5 sites seed |
| 7 | Le modèle supporte-t-il le benchmark et la projection 2030 ? | Le benchmark a besoin de conso_kwh_m2_an par site. La projection a besoin de l'historique. | Vérifier que la donnée existe ou peut être calculée |

### Documents / captures / pages à fournir pour l'audit

| Document | Source | Comment l'obtenir |
|----------|--------|-------------------|
| Captures pages patrimoine (accueil, liste sites, detail site, 360) | Playwright audit agent | `node audit-agent.mjs --pages patrimoine,site-detail,site-360` |
| Schéma modèle de données (tables Org, Site, Batiment, Compteur) | Backend models/ | `Read models/site.py, models/batiment.py, models/organisation.py` |
| API endpoints patrimoine | Backend routes/ | `Read routes/patrimoine.py, routes/sites.py` |
| Seed démo 5 sites HELIOS | Backend services/demo_seed/ | `Read gen_sites.py` — vérifier usages, surfaces, zones |
| Résultat requête cohérence | SQLite direct | `SELECT COUNT(*) FROM sites WHERE org_id IS NULL; SELECT COUNT(*) FROM batiments WHERE site_id NOT IN (SELECT id FROM sites)` |

### Critères de jugement

| Critère | Seuil GO | Seuil ALERTE | Seuil BLOQUANT |
|---------|----------|-------------|----------------|
| Champs benchmark présents dans modèle Site | 100% (usage, zone, surface, conso) | 75% (1 champ manquant) | < 50% |
| Hiérarchie cohérente (0 orphelins) | 0 orphelin | 1-2 orphelins | > 2 orphelins |
| CVC porté au bon niveau (bâtiment) | Sur Batiment | Sur Site (mais somme cohérente) | Nulle part |
| Navigation UI < 3 clics vers détail | ≤ 3 clics | 4 clics | > 4 clics ou 404 |
| 5 usages distincts dans seed | 5 usages distincts | 4 usages (1 doublon) | < 4 usages |
| Temps de chargement page patrimoine | < 2s | 2-5s | > 5s |

### Liens obligatoires avec les autres briques

| Brique | Lien avec patrimoine | Ce que l'audit doit vérifier |
|--------|---------------------|------------------------------|
| **Conformité** | Obligation → Site, Finding → Site | Chaque obligation a un site_id valide. Chaque finding a un site_id. |
| **Consommation** | Compteur → Site, conso_kwh_m2_an → Site | La conso est rattachée au bon site. Le calcul kWh/m² est cohérent. |
| **Facturation** | Facture → Site (via contrat/compteur) | La facture est traçable jusqu'au site. |
| **Achat** | Contrat → Site(s) | Un contrat couvre 1..n sites. Le lien est navigable. |
| **Benchmark** | BenchmarkRef matching → Site.usage + zone + surface | Le site a les champs nécessaires au matching. |
| **Preuves** | ProofFile → Obligation → Site | La preuve remonte jusqu'au site via l'obligation. |
| **Actions** | ActionItem → Site | L'action est rattachée au bon site. |

### Sortie attendue de l'audit

1. **Tableau de conformité modèle** : champ par champ, présent/absent/partiel
2. **Liste des incohérences** : orphelins, champs vides, surfaces incohérentes
3. **Captures annotées** : chaque page patrimoine avec commentaires GO/ALERTE/BLOQUANT
4. **Recommandations** : max 5, priorisées, avec effort estimé
5. **Verdict** : GO / GO AVEC RÉSERVES / BLOQUANT

---

## 8. TOP 5 ACTIONS FINALES

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| 1 | **Communiquer la baseline figée** à l'équipe : envoyer ce document, confirmer les 4 paris, le scope out, les gates | 0.5h | Product Owner | Mardi 11 mars |
| 2 | **Démarrer Sprint 1** : créer le modèle ProofFile + API REST proofs + tests pytest | 4j | Lead dev | Vendredi 14 mars |
| 3 | **Préparer le seed benchmark** : télécharger les données ADEME/CEREN, structurer le fichier JSON/CSV de référence pour 6 usages × 3 zones | 0.5j | Lead dev ou Product | Avant S7 (18 avril) |
| 4 | **Créer le fichier review vendredi** : copier le template 6D dans un fichier `REVIEW_HEBDO.md`, initialiser la première review S1 | 15 min | Product Owner | Vendredi 14 mars |
| 5 | **Bloquer les dates des 3 démos prospects** (cible post-G2) : identifier 3 prospects, bloquer des créneaux fin mai / début juin | 1h | Business / Product | Avant fin S8 (2 mai) |

---

> **Ce document ne remplace pas le plan.**
> **Il le rend pilotable.**
>
> *Le plan dit quoi faire. Ce document dit comment savoir si on le fait bien.*
