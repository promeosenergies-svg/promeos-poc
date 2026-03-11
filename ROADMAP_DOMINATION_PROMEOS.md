# ROADMAP DE DOMINATION PROMEOS — 12 MOIS

> **Date** : 11 mars 2026
> **Auteur** : CPO / Principal Product Strategist
> **Version** : 1.0

---

## 1. THÈSE DE DOMINATION PRODUIT

**Position actuelle** : PROMEOS est un cockpit énergie-patrimoine multi-sites qui a déjà franchi le cap du POC. La brique Conformité couvre 3 cadres réglementaires réels (Décret Tertiaire, BACS, APER) avec moteur YAML versionné, score unifié pondéré, workflow findings, Guided Mode, export OPERAT CSV, modèle riche, et logique multi-sites. Le cockpit intègre aussi consommation (monitoring, usages horaires, diagnostic), facturation (shadow billing, anomalies), achat (scénarios, renouvellements), patrimoine (sites, bâtiments, segmentation), et un plan d'actions unifié. La base technique est solide : FastAPI, SQLite, React/Vite, 5586 tests green, seed démo crédible sur 5 sites.

**Ce qui manque** : le lien conformité→conso→facture n'est pas encore visible, le coffre de preuves n'est pas persisté, le benchmark sectoriel est absent, la projection temporelle n'existe pas, et l'export comité est embryonnaire. Le vrai gap n'est pas technique — c'est le passage de "dashboard qui montre" à "plateforme qui prouve et qui fait agir".

**Wedge principal** : **Conformité énergétique multi-sites exécutable et opposable** — la seule plateforme qui va de l'assujettissement à la preuve, en passant par l'action, avec traçabilité complète.

**Wedge secondaire** : Cockpit décisionnel post-audit / post-OPERAT relié à l'impact financier.

**Wedge long terme** : Plateforme de pilotage énergie-patrimoine-conformité unifiée pour le tertiaire français et européen.

> *PROMEOS transforme les obligations réglementaires en actions opérationnelles prouvées — du diagnostic au dossier opposable, relié à la consommation réelle et à l'impact financier.*

---

## 2. VERDICT STRATÉGIQUE

### FAITS — Ce que PROMEOS possède déjà

| Capacité | Niveau | Rareté marché |
|----------|--------|---------------|
| 3 cadres réglementaires couverts (DT + BACS + APER) | Fonctionnel | Rare — la plupart ne font que DT ou BACS isolément |
| Moteur YAML versionné avec assujettissement explicable | Solide | Très rare — aucun SaaS concurrent n'a ça open |
| Score unifié pondéré avec externalisation des poids | Solide | Unique |
| UX dual public/expert sans JSON brut | Solide | Rare |
| Workflow findings (open→ack→resolved→false_positive) | Fonctionnel | Standard mais bien intégré |
| Shadow billing 5 composantes + catalogue versionné | Avancé | Différenciant |
| Plan d'actions unifié cross-sources | Fonctionnel | Rare dans le compliance pur |
| Seed démo crédible (5 sites, 15 findings, 12 actions) | Prêt | Avantage démo réel |
| 5586 tests, CI green, architecture propre | Solide | Fondation fiable |

#### Ce qui est rare et défensif

- **Le lien patrimoine → obligation → finding → action → preuve** existe en data. Aucun concurrent SaaS ne fait cette chaîne complète.
- **L'explicabilité du moteur** (inputs_json, params_json, engine_version, base légale, options) est un atout expert majeur.
- **Le shadow billing relié au patrimoine** est un angle unique conformité+facturation.

### Ce qui est encore faible

| Gap | Sévérité | Impact |
|-----|----------|--------|
| Coffre de preuves non persisté (state React uniquement) | **Critique** | Bloque l'opposabilité |
| Benchmark sectoriel absent | **Fort** | Bloque la crédibilité DG |
| Projection temporelle absente (où serai-je en 2030 ?) | **Fort** | Bloque le narratif long terme |
| Simulation "si j'agis" absente | **Moyen** | Bloque l'arbitrage |
| Export comité / PDF opposable | **Fort** | Bloque la monétisation |
| Lien conformité → conso réelle non visible en UI | **Fort** | Bloque la différenciation cockpit |
| APER sous-modélisée (pas de calcul surface/puissance) | **Moyen** | Bloque la couverture 3 cadres |
| Notifications réglementaires proactives absentes | **Moyen** | Bloque la rétention |

### HYPOTHÈSES — Ce qui peut devenir moat

1. **Le coffre de preuves persisté + versionné** peut devenir le premier moat défensif : une fois que le client dépose ses preuves dans PROMEOS, il ne part plus.
2. **Le benchmark sectoriel** (même basique : médiane par usage/surface/zone climat) crédibilise le score et justifie un pricing premium.
3. **La projection 2030/2040** avec trajectoire DT crée un narratif long terme que les cabinets ne font pas en continu.
4. **L'intégration conformité→conso→facture** est le vrai différenciant cockpit — aucun dashboard conformité ne sait montrer "votre non-conformité BACS vous coûte X€/an en surconsommation".

### DÉCISIONS — Où concentrer la domination

**Faire** :
- Coffre de preuves persisté (mois 1-2) — c'est le verrou d'adoption
- Benchmark sectoriel basique (mois 2-3) — crédibilité DG
- Projection DT 2030 (mois 3-4) — narratif long terme
- Export dossier comité PDF (mois 2-3) — monétisation
- Lien conformité→conso visible en UI (mois 3-4) — différenciation

**Ne pas faire** :
- Pas de module GTB/BMS complet — rester sur l'attestation/compliance BACS, pas la supervision
- Pas de marketplace connecteurs avant d'avoir le coffre de preuves
- Pas de module achat énergie complexe (trading, fixing) — rester sur scénarios simples
- Pas d'IA générative sur la conformité — le moteur YAML explicable est plus crédible
- Pas de multi-tenant SaaS avant 10 clients payants

---

## 3. MOAT PRODUIT — 7 avantages concurrentiels défensables

| # | Avantage | Concret | Défensabilité |
|---|----------|---------|---------------|
| 1 | **Source de vérité réglementaire versionnée** | Moteur YAML avec rule_id, version, valid_from/to, changelog | Fork-proof : le travail de modélisation réglementaire est cumulatif |
| 2 | **Coffre de preuves opposable** (cible) | Upload, versioning, horodatage, inclusion PDF, traçabilité | Lock-in : les preuves sont dans PROMEOS, le client ne migre plus |
| 3 | **Moteur d'assujettissement explicable** | inputs_json, params_json, base légale, engine_version visibles | Trust : l'expert peut auditer chaque décision |
| 4 | **Conformité reliée à la consommation réelle** (cible) | Widget kWh/m²/an dans obligation DT, lien vers monitoring | Unique : aucun outil conformité ne montre la conso réelle |
| 5 | **Conformité reliée à l'impact facture** (cible) | Delta facture si conformité atteinte, shadow billing | Unique : aucun outil conformité ne chiffre l'impact financier |
| 6 | **Benchmark sectoriel contextualisé** (cible) | Médiane/P25/P75 par usage×zone×surface vs site client | Crédibilité DG : le score a un référentiel |
| 7 | **Dossier comité auto-généré** (cible) | PDF avec score + benchmark + preuves + actions + tendance | Monétisation : le livrable justifie l'abonnement |

---

## 4. ROADMAP 12 MOIS

### H1 — 0–30 JOURS : "Coffre & Dossier"

> **Objectif** : Rendre PROMEOS opposable — les preuves sont persistées, le dossier est exportable.

| Initiative | Classe | Livrables | Dépendance | Preuve de succès |
|-----------|--------|-----------|------------|-----------------|
| **Coffre de preuves persisté** | Must win | Backend: modèle ProofFile (blob/S3), API upload/list/delete par obligation. Frontend: remplacement du state React par appels API. Versionning: hash + date + uploader. | Modèle Evidence existant à enrichir | Un utilisateur upload une preuve, fait F5, la retrouve |
| **Export dossier PDF** | Must win | Backend: WeasyPrint/wkhtmltopdf, endpoint GET /compliance/dossier/{org_id}/pdf. Contenu: score, obligations, findings, preuves jointes, top urgences, signature date. | Coffre preuves (pour inclure les fichiers) | PDF téléchargeable avec score + preuves |
| **Notifications échéances** | Strong diff | Backend: cron hebdo, calcul J-90/J-30/J-0 par obligation. Frontend: badge dans Notifications existant. Email digest optionnel. | Modèle Obligation.echeance existant | Email "Échéance BACS dans 30 jours" reçu |
| **APER calcul surface/puissance** | Strong diff | Backend: enrichir APER engine avec calcul puissance crête estimée (kWc/m²), coût estimé, ROI simplifié. Frontend: afficher dans obligation APER. | Données parking_area_m2 / roof_area_m2 existantes | kWc estimé visible dans obligation APER |

**Risques** :
- Upload fichier volumeux → limiter à 10 Mo, types PDF/JPG/PNG
- WeasyPrint complexe sur Windows → alternative : génération HTML + print CSS

---

### H2 — 31–90 JOURS : "Benchmark & Trajectoire"

> **Objectif** : Rendre PROMEOS crédible face aux experts — benchmark sectoriel + projection DT 2030.

| Initiative | Classe | Livrables | Dépendance | Preuve de succès |
|-----------|--------|-----------|------------|-----------------|
| **Benchmark sectoriel** | Must win | Backend: table benchmark_refs (usage, zone_climat, surface_tranche, conso_kwh_m2_median, p25, p75). Seed: données ADEME/CEREN publiques. Frontend: widget "Votre site vs médiane secteur" dans ObligationsTab DT. | Données conso par site existantes | Widget "vs médiane" visible en démo |
| **Projection trajectoire DT 2030/2040** | Must win | Backend: service projection_trajectory (conso actuelle, objectif -40%/-60%, année cible). Courbe projetée vs objectif. Frontend: chart sparkline dans obligation DT + section dédiée. | Benchmark + conso réelle | Courbe projetée avec gap visible |
| **Lien conformité → consommation visible** | Strong diff | Frontend: dans chaque obligation DT, lien "Voir la consommation de ce site" → /consommations?site=X. Widget résumé conso kWh/m²/an dans la carte obligation. | API conso existante | Widget conso dans obligation DT |
| **Lien conformité → facture visible** | Strong diff | Frontend: dans le dossier, section "Impact financier estimé" — delta facture si conformité DT atteinte. | Shadow billing existant | Section "impact facture" dans dossier |
| **Workflow multi-acteurs** | Nice to have | Backend: champ assigned_to sur findings/actions avec rôle (propriétaire, locataire, mandataire). Frontend: filtre "Mes actions" par rôle. | Modèle User/Role existant | Filtre "mes obligations" par rôle |

**Risques** :
- Données benchmark ADEME parfois obsolètes → prévoir mise à jour annuelle
- Projection linéaire trop simpliste → documenter les hypothèses

---

### H3 — 3–6 MOIS : "Simulation & Automatisation"

> **Objectif** : Rendre PROMEOS actionnable — simulation d'impact, connexion données auto, rapports automatiques.

| Initiative | Classe | Livrables | Dépendance | Preuve de succès |
|-----------|--------|-----------|------------|-----------------|
| **Simulation "si j'agis"** | Must win | Backend: service impact_simulator (action → réduction conso estimée → impact score → impact facture). Frontend: drawer "Simuler l'impact" sur chaque action, avec avant/après. | Projection + shadow billing | Drawer avec score +26pts, conso -15%, facture -12k€ |
| **Connecteur OPERAT auto** | Strong diff | Backend: import CSV enrichi OPERAT, sync automatique des déclarations, détection écarts PROMEOS vs OPERAT. | Export OPERAT CSV existant | Sync CSV automatique |
| **Rapports périodiques auto** | Strong diff | Backend: cron mensuel, génération PDF automatique. Frontend: section "Rapports" dans Preuves tab avec historique. | Export PDF (H1) | PDF mensuel auto-généré |
| **Alertes réglementaires intelligentes** | Strong diff | Backend: veille simplifiée (YAML mis à jour avec changelog). Frontend: banner "Nouvelle version réglementaire" + diff avant/après. | Moteur YAML versionné | Banner "nouvelle version" |
| **BACS profond : inspections + maintenance** | Nice to have | Backend: enrichir BacsInspection avec calendrier maintenance, rappels. Frontend: timeline maintenance dans obligation BACS. | Modèle BacsAsset existant | Timeline maintenance visible |

**Risques** :
- Simulation trop simpliste → utiliser des ratios ADEME documentés
- API OPERAT pas encore disponible → fallback CSV

---

### H4 — 6–12 MOIS : "Plateforme & Scale"

> **Objectif** : Rendre PROMEOS incontournable — multi-tenant, API, intégrations, lock-in données.

| Initiative | Classe | Livrables | Dépendance | Preuve de succès |
|-----------|--------|-----------|------------|-----------------|
| **Multi-tenant SaaS** | Must win | Backend: isolation org complète, onboarding self-service, billing Stripe. Frontend: parcours onboarding guidé. | Architecture actuelle déjà org-scoped | Onboarding < 30 min |
| **API publique conformité** | Strong diff | REST API documentée : GET /compliance/score, GET /compliance/obligations, POST /compliance/evaluate. Webhooks sur changements. | Endpoints existants à formaliser | 1 intégrateur utilise l'API |
| **Intégrations GTB/BMS** | Strong diff | Connecteurs : Schneider EcoStruxure, Siemens Desigo, Honeywell Niagara — import données BACS automatique. | Modèle BacsAsset existant | 1 intégration GTB live |
| **Marketplace preuves** | Nice to have | Templates de preuves par obligation (modèle attestation BACS, template déclaration OPERAT). | Coffre preuves (H1) | 3 templates disponibles |
| **ACC / Autoconsommation collective** | Not now | Nouveau cadre réglementaire ACC dans le moteur YAML. | Maturité réglementaire ACC | — |

**Risques** :
- Multi-tenant : migration données existantes
- Intégrations GTB : dépendance API vendeurs

---

## 5. PRODUIT VS MARCHÉ

| Capacité | PROMEOS aujourd'hui | Niveau cible 12 mois | Pourquoi ça bat le marché | Preuve à produire |
|----------|--------------------|-----------------------|--------------------------|------------------|
| Assujettissement multi-cadre | 3 cadres, YAML versionné | 4+ cadres, calcul auto | Les cabinets font du one-shot PDF. PROMEOS fait du continu explicable. | Démo : "Montrez-moi votre moteur" → aucun concurrent ne peut |
| Coffre de preuves | State React (non persisté) | Persisté, versionné, horodaté, exportable | Les GTB n'ont pas de coffre. Les dashboards n'ont pas de preuves. | Audit : "Où sont vos preuves BACS ?" → dans PROMEOS |
| Score unifié | 46/100 avec pondération | + benchmark + tendance + projection | Les cabinets donnent un score ponctuel. PROMEOS donne un score vivant. | Comité : PDF avec score + trajectoire + benchmark |
| Lien conformité→conso | Existe en data, pas visible | Widget conso dans obligation + impact facture | Aucun outil conformité ne montre la conso réelle. | Démo : "Non-conformité DT = surcoût 15k€/an" |
| Simulation impact | Absent | Avant/après par action | Les cabinets font des recommandations sans chiffrage continu. | Démo : "Si GTB → score +26pts, facture -12k€" |
| Projection 2030 | Absent | Courbe trajectoire vs objectif DT | Aucun SaaS ne fait la projection continue. | Widget : "Gap 2030 : 12 points" |
| Benchmark sectoriel | Absent | Médiane/P25/P75 par usage/zone | Cabinets ont le benchmark sans cockpit. SaaS ont le cockpit sans benchmark. | Widget : "Votre bureau au P75 IDF" |
| Export comité | DossierPrintView basique | PDF complet auto-généré | Les cabinets font des rapports. PROMEOS fait des dossiers vivants. | PDF montrable en CA |
| Workflow multi-acteurs | Monolithique | Propriétaire / locataire / mandataire | GTB et dashboards sont mono-acteur. | Parcours par rôle |
| Notifications proactives | Absent | J-90/J-30/J-0 + veille réglementaire | Personne ne notifie proactivement. | Email J-30 reçu |

---

## 6. PLAN DÉMO & PREUVES

### Parcours démo standard (15 min)

| Étape | Durée | Ce qu'on montre | Message clé |
|-------|-------|-----------------|-------------|
| 1. Cockpit | 1 min | Vue d'ensemble patrimoine, KPIs, alertes | "Tout votre patrimoine en un coup d'œil" |
| 2. Conformité — Entrée | 2 min | Score 46/100, top 3 urgences, résumé exécutif | "Vous savez immédiatement où agir" |
| 3. Obligation BACS expandée | 3 min | Base légale, options, pénalité, "Échéance dépassée", preuves attendues | "Chaque obligation est explicable et actionnable" |
| 4. Mode Expert | 1 min | Toggle → formule, inputs structurés, engine version | "L'expert peut auditer chaque calcul" |
| 5. Preuves | 2 min | Complètes / Partielles / Manquantes, upload | "Vous constituez votre dossier opposable" |
| 6. Plan d'exécution | 2 min | Finding → action → preuve, badges lifecycle | "La boucle est complète : diagnostic → preuve" |
| 7. Dossier | 1 min | PDF avec score + obligations + preuves | "Votre dossier comité en 1 clic" |
| 8. Lien conso + facture | 2 min | Shadow billing, anomalies, impact | "La conformité a un impact financier mesurable" |
| 9. Actions | 1 min | Plan d'actions unifié cross-sources | "Toutes vos actions au même endroit" |

### 5 scénarios de domination

#### A — vs Cabinet efficacité énergétique

- **Situation** : Le prospect a payé un audit 15k€ il y a 2 ans. Le rapport PDF est dans un tiroir.
- **Démo PROMEOS** : "Votre score conformité est à 46/100. L'audit disait quoi ? Vous ne savez plus. Chez nous, le score est vivant : il se met à jour quand vous agissez."
- **Kill shot** : "Le cabinet vous donne un rapport. PROMEOS vous donne un cockpit. Le rapport vieillit. Le cockpit vit."

#### B — vs GTB / Smart Building

- **Situation** : Le prospect a une GTB Schneider sur 3 sites, mais ne sait pas s'il est conforme BACS.
- **Démo PROMEOS** : "Votre GTB gère le bâtiment. PROMEOS gère votre conformité. Votre GTB ne sait pas que l'échéance BACS haute puissance est dépassée depuis 14 mois."
- **Kill shot** : "La GTB est l'outil. PROMEOS est le pilote."

#### C — vs Dashboard conformité classique (Deepki, Energisme)

- **Situation** : Le prospect utilise un dashboard énergie qui affiche des KPIs mais pas de conformité actionnable.
- **Démo PROMEOS** : "Votre dashboard montre votre consommation. Mais est-ce que votre bureau Lyon est assujetti BACS ? À quelle échéance ? Avec quelles preuves ?"
- **Kill shot** : "Ils montrent des courbes. Nous montrons des obligations, des actions, et des preuves."

#### D — vs Excel / manuel

- **Situation** : L'energy manager gère la conformité dans un Excel avec 15 onglets.
- **Démo PROMEOS** : "Votre Excel ne vous alerte pas quand une échéance approche. Il ne vous dit pas quelle preuve manque. Et il n'est pas montrable en comité."
- **Kill shot** : "Votre Excel vous coûte du temps. PROMEOS vous fait gagner du temps ET de la crédibilité."

#### E — vs Rien (prospect qui découvre)

- **Situation** : Le DG ne sait pas qu'il est assujetti au Décret Tertiaire.
- **Démo PROMEOS** : "Vous avez 5 sites tertiaire > 1000 m². Vous êtes assujetti. Votre échéance OPERAT est dans 9 mois. Votre trajectoire -40% n'est pas atteinte."
- **Kill shot** : "Avant PROMEOS, vous ne saviez pas. Après PROMEOS, vous savez ET vous agissez."

### KPIs à suivre

| KPI | Cible 6 mois | Cible 12 mois | Pourquoi |
|-----|-------------|---------------|---------|
| Nb organisations actives | 5 | 20 | Adoption |
| Nb preuves déposées / org | 3 | 10 | Lock-in |
| Nb dossiers PDF générés / mois | 10 | 50 | Usage comité = preuve de valeur |
| Score conformité moyen | 45 | 65 | Progression = valeur perçue |
| Taux de retour hebdo | 30% | 50% | Stickiness |
| Nb actions créées depuis conformité | 20 | 100 | Actionnabilité |
| Temps moyen onboarding → 1er score | 2h | 30 min | Adoption self-service |

### Signaux faibles à surveiller

- Si personne ne dépose de preuve → le coffre n'a pas de valeur perçue → retravailler l'UX d'upload
- Si le PDF n'est jamais téléchargé → le format/contenu ne convainc pas → tester avec 3 prospects
- Si le score ne change jamais → les actions ne sont pas liées aux findings → vérifier la boucle
- Si l'expert n'active jamais le mode Expert → le toggle n'est pas assez visible → A/B test position

---

## 7. BACKLOG ICE FINAL

| # | Initiative | Problème résolu | Impact | Conf. | Ease | ICE | Owner | Horizon | Preuve attendue |
|---|-----------|----------------|--------|-------|------|-----|-------|---------|----------------|
| 1 | **Coffre preuves persisté** | Preuves perdues au refresh | 10 | 9 | 7 | **630** | Back+Front | 0–30j | Upload + retrieval + inclusion PDF |
| 2 | **Notifications échéances** | Pas d'alerte proactive | 8 | 9 | 7 | **504** | Back | 0–30j | Email J-90 reçue |
| 3 | **Export dossier PDF** | Pas de livrable comité | 9 | 9 | 6 | **486** | Back | 0–30j | PDF avec score+preuves |
| 4 | **APER calcul puissance** | APER sous-modélisé | 7 | 8 | 7 | **392** | Back | 0–30j | kWc estimé affiché |
| 5 | **Lien conformité→conso UI** | Cockpit cloisonné | 8 | 8 | 6 | **384** | Front | 31–90j | Widget conso dans obligation |
| 6 | **Benchmark sectoriel** | Score sans contexte | 9 | 7 | 6 | **378** | Back+Front | 31–90j | Widget "vs médiane" |
| 7 | **Projection DT 2030** | Pas de narratif long terme | 9 | 8 | 5 | **360** | Back+Front | 31–90j | Courbe projetée visible |
| 8 | **Lien conformité→facture** | Impact financier invisible | 8 | 7 | 5 | **280** | Front | 31–90j | Section impact dans dossier |
| 9 | **Rapports périodiques auto** | Pas de suivi temporel | 7 | 8 | 5 | **280** | Back | 3–6m | PDF mensuel auto-généré |
| 10 | **Simulation "si j'agis"** | Pas d'arbitrage quantifié | 9 | 7 | 4 | **252** | Back+Front | 3–6m | Drawer avant/après |
| 11 | **API publique conformité** | Pas d'intégration externe | 7 | 7 | 5 | **245** | Back | 6–12m | Endpoint documenté |
| 12 | **Veille réglementaire push** | Changements non détectés | 6 | 6 | 5 | **180** | Back | 3–6m | Banner "nouvelle version" |
| 13 | **Workflow multi-acteurs** | Mono-utilisateur | 6 | 7 | 4 | **168** | Back+Front | 3–6m | Filtre par rôle |
| 14 | **Connecteur OPERAT auto** | Import manuel | 7 | 6 | 4 | **168** | Back | 3–6m | Sync CSV auto |
| 15 | **Multi-tenant SaaS** | Scalabilité bloquée | 8 | 6 | 3 | **144** | Arch | 6–12m | Onboarding self-service |

---

## 8. TOP 5 ACTIONS IMMÉDIATES

| # | Action | Effort | Owner | Deadline | Sert |
|---|--------|--------|-------|----------|------|
| 1 | **Coffre preuves persisté** : modèle ProofFile backend + API REST + migration state React → API | 5j back + 2j front | Lead dev | J+14 | Moat + adoption + démo |
| 2 | **Export PDF dossier complet** : endpoint WeasyPrint, score + obligations + preuves jointes + urgences | 3j back + 1j front | Lead dev | J+21 | Monétisation + démo |
| 3 | **Notifications échéances** : cron J-90/J-30/J-0, module Notifications existant, email digest | 3j back + 1j front | Lead dev | J+21 | Rétention + valeur perçue |
| 4 | **APER enrichi** : calcul puissance crête, coût estimé, ROI dans moteur + affichage obligation | 2j back + 1j front | Lead dev | J+10 | Couverture + crédibilité |
| 5 | **Benchmark sectoriel V0** : table références ADEME, seed 10 usages × 3 zones, widget "vs médiane" | 3j back + 2j front | Lead dev | J+45 | Crédibilité DG + démo |

---

## SÉQUENCE DE DOMINATION

```
Mois 1-2    →  CRÉDIBILITÉ        Coffre preuves + PDF + notifications
Mois 2-3    →  OPPOSABILITÉ       Benchmark + projection + liens conso/facture
Mois 3-6    →  AUTOMATISATION     Simulation + connecteurs + rapports auto
Mois 6-9    →  BENCHMARK          API publique + intégrations GTB
Mois 9-12   →  PLATEFORME         Multi-tenant + marketplace + scale
```

> Le but n'est pas de faire plus de fonctionnalités.
> Le but est de verrouiller la chaîne **Patrimoine → Obligation → Risque → Action → Preuve → Impact** de manière si complète et si crédible que le client ne peut plus s'en passer.
