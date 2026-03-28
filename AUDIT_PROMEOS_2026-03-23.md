# AUDIT SÉVÈRE PROMEOS POC — 23 mars 2026 (v2 — consolidé)

> Audit complet sans complaisance du POC PROMEOS (cockpit énergétique B2B post-ARENH).
> Méthode : 3 étapes d'audit progressif (cadrage → fil conducteur → règles métier), 9 agents d'exploration parallèles, vérification fichier/ligne/formule, sources réglementaires officielles vérifiées (web search).
> Repo : 3 326 fichiers Python backend, 462 endpoints API, 50 pages frontend (32 823 lignes JSX), 226 tests backend, 35 tests frontend, 24 specs E2E Playwright.

---

## 1. VERDICT EXÉCUTIF

| | |
|---|---|
| **Note globale** | **7.0 / 10** (corrigée de 6.5 après vérification — le POC est plus avancé que l'audit initial ne le laissait croire) |
| **Peut-on viser 9/10 marché ?** | **OUI SOUS CONDITIONS** |
| **Note atteignable à 90 jours** | **8.5 / 10** |

### Corrections majeures par rapport à l'audit initial

L'audit approfondi (étapes 0-1-2) a révélé que **3 constats P0 de l'audit initial étaient factuellement faux** :

| Constat initial | Réalité vérifiée | Preuve |
| --- | --- | --- |
| "Trajectoire DT non calculée" (P0) | **FAUX** — `dt_trajectory_service.py:162` calcule `(1 − conso_actuelle/conso_ref) × 100`. `operat_trajectory.py:242` calcule delta kwh + statut. **Le vrai problème** : `update_site_avancement()` (ligne 181) existe mais a **0 appelant** | `dt_trajectory_service.py`, `operat_trajectory.py` |
| "APER = coquille vide" (P0) | **FAUX** — `aper_service.py` (251L) implémente éligibilité réelle (parking ≥ 1500m² outdoor, toiture ≥ 500m², deadlines 2026-2028). Évaluateur RegOps APER existe aussi (`regops/rules/aper.py`, 110L, 4 règles) | `aper_service.py`, `regops/rules/aper.py` |
| "Pas de data dictionary" (P1) | **FAUX** — `docs/data-dictionary.md` existe (1677 lignes) | `docs/data-dictionary.md` |

**Le vrai risque = déconnexions entre briques existantes**, pas absence de briques.

### Top 5 Forces

1. **BACS Engine = 8.5/10** — Putile exact (cascade/réseau/indépendant), TRI art. R.175-7, inspections quinquennales, compliance gate prudent, 8 types preuves, workflow exemption DRAFT→SUBMITTED→APPROVED/REJECTED→EXPIRED, 10 exigences fonctionnelles R.175-3, alertes automatiques. Le meilleur asset réglementaire du POC
2. **Architecture modulaire mature** — 60 routers (462 endpoints), séparation modèles/services/routes/schemas, YAML-driven rules, scoring unifié A.2 configurable, compliance_coordinator orchestrant 3 chemins synchronisés
3. **Bill Intelligence crédible** — Shadow billing V2 avec reconstitution composant par composant, TURPE 7 taux CRE officiels (délibération n°2025-78), 10 règles anomalie, résolution prix multi-niveaux
4. **Frontend riche et cohérent** — Design system unifié (40 composants UI), skeletons/empty/error states, ScopeContext 3 niveaux, ConsoSourceBadge/DataQualityBadge/FreshnessIndicator/TrustBadge, Explain/glossaire intégré
5. **CI/CD professionnelle + test coverage** — 4 106 fonctions test backend, 35 tests Vitest, 24 specs Playwright E2E, quality gate 3 étages (ruff + mypy + pytest + Playwright)

### Top 10 Faiblesses (corrigées et précisées)

1. **KPI avancement DT déconnecté de la trajectoire dynamique** — `kpi_service.py:218` lit `AVG(Site.avancement_decret_pct)` = moyenne champs plats, alors que `dt_trajectory_service.py:162` calcule la vraie trajectoire. `update_site_avancement()` (ligne 181) existe mais a 0 appelant
2. **Scénarios achat = facteurs prix hardcodés** — `price_factor: 1.05/0.95/0.88` identiques tous sites/périodes (`purchase_scenarios_service.py:40,69,100`)
3. **Conformité ↔ Facture = rupture totale** — 0 référence croisée entre `ConformitePage.jsx` et `BillIntelPage.jsx` (grep bilatéral = 0 résultat)
4. **`regs.yaml:66` contient une deadline BACS erronée** — Indique 2027-01-01 avec commentaire inversé. Le décret n°2025-1343 du 26/12/2025 a **repoussé** la deadline 70kW de 2027 à 2030 (alignement EPBD). Le code legacy (`compliance_engine.py:53`) et le YAML BACS (`regulations/bacs/v2.yaml:12`) sont corrects à 2030
5. **Scoring YAML déclare 5 frameworks mais seuls 3 ont un évaluateur** — `regs.yaml` pèse DPE Tertiaire (15%) et CSRD (10%) sans évaluateur implémenté. Score correct par accident (frameworks non évalués exclus du dénominateur)
6. **Actions achat éphémères** — `purchase_actions_engine.py` calcule 5 types d'actions mais ne les persiste pas sans appel explicite `POST /api/actions/sync`
7. **CVC estimation aléatoire** — `onboarding_service.py:59` utilise `random.uniform()`. Même site créé 2 fois = obligation BACS potentiellement différente
8. **Dual prix par défaut** — `billing_service.py:43` (0.15 EUR/kWh via env) vs `config/default_prices.py:10` (0.18 EUR/kWh hardcodé)
9. **Confidence non affichée dans les badges UI** — Le backend expose `confidence: high/medium/low` mais l'UI ne l'affiche que dans le dossier print
10. **APER sans obligations ni preuves** — Dashboard éligibilité + estimation PV fonctionnels, mais pas de workflow de mise en conformité (pas d'obligations auto-créées, pas de preuves structurées)

---

## 2. SCORE DÉTAILLÉ PAR AXE (corrigé)

| Axe | Note | Justification |
| --- | --- | --- |
| Produit / logique | **7/10** | Histoire claire, parcours logique, mais rupture conformité↔facture et achat→actions éphémères |
| UX / UI | **7/10** | Design system cohérent, Explain/glossaire, états bien gérés. Confidence non affichée, breakdown score non systématique |
| Front | **7.5/10** | 68 composants réutilisables, 35 tests, skeletons partout. KpiCard 4 variantes (à unifier) |
| Back / API | **7.5/10** | 462 endpoints structurés, error handling avec correlation_id, compliance_coordinator 3 étapes, audit trail ComplianceEventLog |
| Données / Modèle métier | **6.5/10** | 60 modèles, hiérarchie org→site propre, TertiaireEfaConsumption avec source/reliability/normalization. Soft-delete incohérent |
| Règles métier / conformité | **7/10** | BACS 8.5/10 (meilleur asset), DT 6.5/10 (formule existe mais déconnectée du KPI), APER 6/10 (éligibilité réelle, pas de workflow) |
| Facturation / achat | **5.5/10** | Shadow billing V2 fonctionnel, TURPE 7 CRE réel, mais scénarios achat = facteurs fixes |
| Multi-sites / navigation | **7.5/10** | ScopeContext 3 niveaux, breadcrumb, drill-down. Fil conducteur partiel |
| Crédibilité marché | **6/10** | Architecture impressionnante, BACS crédible, mais un expert détectera KPI DT stale et scénarios achat constants |

---

## 3. CONSTATS CRITIQUES (consolidés étapes 0-1-2)

### P0 — Bloquant crédibilité

| # | Problème | Fichier:ligne | Impact | Correctif | Effort |
| --- | --- | --- | --- | --- | --- |
| P0-1 | **`update_site_avancement()` jamais appelé** — KPI DT = champ plat | `dt_trajectory_service.py:181` (0 appelant), `compliance_coordinator.py` (ne l'appelle pas) | Avancement DT statique, ne reflète pas les conso réelles | Ajouter 1 appel dans `compliance_coordinator.recompute_site_full()` | **1 ligne** |
| P0-2 | **Conformité ↔ Facture = aucun lien** | `ConformitePage.jsx` (0 ref billing), `BillIntelPage.jsx` (0 ref compliance) | Rupture entre les 2 briques les plus stratégiques | Bandeau risque financier dans BillIntel + CTA croisés | S |
| P0-3 | **`regs.yaml:66` deadline BACS 70kW = 2027 (FAUX)** | `regs.yaml:66` — commentaire inversé | Config réglementaire erronée. Source officielle : décret n°2025-1343 du 26/12/2025 reporte de 2027 à 2030 | Corriger à `"2030-01-01"` + commentaire décret n°2025-1343 | **XS** |

### P1 — Crédibilité marché

| # | Problème | Fichier:ligne | Correctif | Effort |
| --- | --- | --- | --- | --- |
| P1-1 | Scénarios achat = price_factor fixe (1.05/0.95/0.88) | `purchase_scenarios_service.py:40,69,100` | Intégrer prix moyen marché EPEX 12 mois + spread historique | L |
| P1-2 | Actions achat éphémères — rien dans le centre d'actions sans sync | `purchase_actions_engine.py` vs `action_hub_service.py:302` | Auto-sync à l'ouverture d'ActionsPage ou après calcul scénario | S |
| P1-3 | CVC estimation aléatoire (`random.uniform`) | `onboarding_service.py:59` | Remplacer par médiane du range ou hash(site_id) | XS |
| P1-4 | Scoring YAML déclare 5 fw, seuls 3 implémentés | `regs.yaml:140-145` | Ajouter `implemented: false` sur DPE/CSRD | XS |
| P1-5 | APER sans obligations ni preuves structurées | `aper_service.py` | Créer obligations auto + modèle preuve APER | M |
| P1-6 | Confidence non affichée dans les badges UI | `ConformitePage.jsx` | Ajouter indicateur confidence dans badges | S |
| P1-7 | Dual prix par défaut (0.15 vs 0.18) | `billing_service.py:43` vs `config/default_prices.py:10` | Unifier sur une seule source | XS |

### P2 — Premium

| # | Problème | Correctif | Effort |
| --- | --- | --- | --- |
| P2-1 | Breakdown DT/BACS/APER non affiché systématiquement | Afficher décomposition dans ConformitePage + Cockpit | S |
| P2-2 | TRI BACS nécessite inputs manuels | Auto-estimer coûts depuis ratios sectoriels | L |
| P2-3 | Risque financier sans label "théorique maximum" | Ajouter tooltip/Explain | XS |
| P2-4 | Pas de benchmark sectoriel ADEME/OID | Intégrer ratios par code NAF | L |
| P2-5 | Dégradation panneaux PV non modélisée dans APER | Ajouter facteur ~0.5%/an | S |

---

## 4. CARTOGRAPHIE DU FIL CONDUCTEUR (étape 1)

| Maillon | Note | Statut | Preuve clé |
| --- | --- | --- | --- |
| Patrimoine → Données | **9/10** | IMPLÉMENTÉ | Auto-provision 7 étapes : site→bâtiment→obligations→delivery points→recompute compliance |
| Données → KPI | **6/10** | PARTIEL | `update_site_avancement()` existe mais 0 appelant. KPI DT = champ plat |
| KPI → Conformité | **8/10** | IMPLÉMENTÉ | Même source `compliance_score_service`, cohérent cockpit↔conformité |
| Conformité → Facture | **2/10** | CASSÉ | 0 lien code, 0 lien UI (grep bilatéral = 0 résultat) |
| Facture → Achat | **6/10** | PARTIEL | Volume kWh réel (`EnergyInvoice`), mais price_factor fixe |
| Achat → Actions | **5/10** | PARTIEL | 5 types actions calculés, mais éphémères sans `sync_actions()` |

---

## 5. MOTEUR CONFORMITÉ (étape 2)

### Formules vérifiées

| Calcul | Formule exacte | Fichier:ligne | Correct ? |
| --- | --- | --- | --- |
| Réduction DT | `(1 − conso_actuelle / conso_ref) × 100` | `dt_trajectory_service.py:162` | ✅ |
| Avancement 2030 | `(reduction_pct / 40) × 100`, clampé [0,100] | `dt_trajectory_service.py:163` | ✅ |
| Putile BACS | `max(Σ_cascade, max_indep)` par channel, puis `max(heating, cooling)` | `bacs_engine.py:86-124` | ✅ |
| TRI exemption | `cout_net / (conso × gain% × prix)`, exempt si > 10 ans | `bacs_engine.py:220-276` | ✅ Art. R.175-7 |
| Score A.2 | `Σ(fw_score × weight) / Σ(weight) − min(20, critical × 5)` | `compliance_score_service.py:225-232` | ✅ |
| Risque financier | `7500 × NOK + 3750 × RISK` | `compliance_engine.py:214-216` | ⚠️ Non modulé surface/type |

### Deadlines vérifiées aux sources officielles

| Obligation | Deadline code | Source officielle | Statut |
| --- | --- | --- | --- |
| DT -40% | 2030-12-31 | Décret tertiaire art. R.174-26 | ✅ |
| DT déclaration OPERAT | 2026-09-30 | ADEME (conso 2025) | ✅ |
| BACS > 290 kW | 2025-01-01 | Décret n°2020-887 | ✅ |
| BACS 70-290 kW | 2030-01-01 (code) / 2027-01-01 (regs.yaml) | **Décret n°2025-1343 → 2030** | ✅ code, ❌ regs.yaml |
| APER parking large | 2026-07-01 | Loi n°2023-175 | ✅ |
| APER parking medium | 2028-07-01 | Loi n°2023-175 | ✅ |
| APER toiture | 2028-01-01 | Loi n°2023-175 | ✅ |

---

## 6. PLAN D'ACTION PRIORISÉ (consolidé)

### Immédiat (1-3 jours) — XS

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 1 | Appeler `update_site_avancement(db, site_id)` dans `recompute_site_full()` | `compliance_coordinator.py:76` | **1 ligne** |
| 2 | Corriger `regs.yaml:66` → `"2030-01-01"` + commentaire décret n°2025-1343 | `regops/config/regs.yaml:66` | XS |
| 3 | Ajouter `implemented: false` sur DPE/CSRD dans regs.yaml scoring | `regops/config/regs.yaml:140-145` | XS |
| 4 | Rendre CVC estimation déterministe | `onboarding_service.py:59` | XS |
| 5 | Unifier prix par défaut (0.15 vs 0.18) | `billing_service.py:43`, `config/default_prices.py:10` | XS |

### Court terme (1-2 semaines) — S/M

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 6 | Bandeau risque financier + CTA conformité dans BillIntelPage | `BillIntelPage.jsx` | S |
| 7 | CTA "Voir factures" dans ConformitePage | `ConformitePage.jsx` | XS |
| 8 | Auto-sync actions à l'ouverture d'ActionsPage | `ActionsPage.jsx` | S |
| 9 | Afficher confidence dans badges conformité | `ConformitePage.jsx` | S |
| 10 | Afficher breakdown DT/BACS/APER dans le score | `ComplianceScoreHeader` | S |
| 11 | Créer obligations APER automatiques | `onboarding_service.py` | M |

### Moyen terme (2-4 semaines) — L

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 12 | Scénarios achat dynamiques (prix marché simplifié) | `purchase_scenarios_service.py` | L |
| 13 | Profil HP/HC dans les scénarios achat | `purchase_scenarios_service.py`, `purchase_service.py` | L |
| 14 | Benchmark sectoriel ADEME/OID | `kpi_service.py`, `Site360.jsx`, `Cockpit.jsx` | L |
| 15 | Preuves structurées APER | `models/`, `routes/aper.py` | M |

---

## 7. CHECKLIST QA

### Règles métier & conformité
- [ ] `update_site_avancement()` appelé dans `recompute_site_full()` → KPI DT dynamique
- [ ] `regs.yaml:66` corrigé à 2030 (décret n°2025-1343)
- [ ] DPE/CSRD marqués `implemented: false` dans regs.yaml
- [ ] Score A.2 breakdown affiché (DT/BACS/APER + confidence)
- [ ] Pénalité financière avec label "risque théorique maximum"
- [ ] CVC estimation déterministe

### Fil conducteur
- [ ] Conformité ↔ Facture liés (bandeau + CTA croisés)
- [ ] Actions achat auto-sync ou sync à la navigation
- [ ] Import conso → trigger recompute KPI

### Front
- [ ] Confidence affiché dans badges conformité
- [ ] ConsoSourceBadge distingue seed/metered/billed/estimated
- [ ] Empty/error/loading states testés

### Back
- [ ] Prix fallback unifié (1 source)
- [ ] SIREN/SIRET + surface_m2 validés
- [ ] Pagination sur endpoints liste

---

## 8. DEFINITION OF DONE

Le POC sera considéré **solide et crédible** quand :

1. **KPI DT = trajectoire dynamique** — `update_site_avancement()` appelé, KPI cockpit reflète les consommations réelles
2. **Score conformité = vérifiable** — Breakdown DT/BACS/APER affiché, confidence visible, formule accessible
3. **Fil conducteur complet** — Conformité ↔ Facture liés, Achat → Actions persistées
4. **Scénarios achat = crédibles** — Basés sur données marché, pas un multiplicateur fixe
5. **Config réglementaire = à jour** — Deadlines vérifiées aux sources officielles (décret n°2025-1343 pour BACS)
6. **Données tracées** — Source/reliability/confidence sur chaque donnée, distinguées en UI
7. **Zéro calcul faux** — Pas de placeholder non signalé, pas de config erronée
8. **Un non-expert comprend** — DAF ou directeur immobilier comprend la valeur en < 3 minutes

---

## Top 7 actions qui font le plus monter la note

| # | Action | Impact | Effort |
| --- | --- | --- | --- |
| 1 | Câbler `update_site_avancement()` (1 ligne) | +0.4 | **1 ligne** |
| 2 | Lier Conformité ↔ Facture (bandeau + CTA) | +0.3 | S |
| 3 | Scénarios achat données marché réelles | +0.4 | L |
| 4 | Corriger regs.yaml (deadline + DPE/CSRD flags) | +0.2 | XS |
| 5 | Auto-sync actions achat | +0.2 | S |
| 6 | Afficher breakdown + confidence score | +0.2 | S |
| 7 | Benchmark sectoriel ADEME/OID | +0.3 | L |

**7.0 + 2.0 = 9.0/10 atteignable.**

---

## Annexe — Sources réglementaires vérifiées (×2 minimum par point)

*Vérification du 2026-03-23. Chaque point sensible vérifié avec au moins 2 sources, source primaire officielle prioritaire.*

### BACS — Deadline 70kW

| Point | Source 1 (primaire) | Source 2 | Retenue | Raison |
| --- | --- | --- | --- | --- |
| Deadline 70-290kW | [Légifrance — Décret n°2025-1343](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053175245) (JO 27/12/2025) : remplace "2027" par "2030" dans art. R175-2 | [Légifrance — Art. R175-2 consolidé](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000053216492) : texte en vigueur confirme 2030 | **2030-01-01** | 2 sources primaires Légifrance concordantes |
| Seuils Putile | [Légifrance — Art. R175-2 consolidé](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000053216492) : >290kW puis >70kW | [Légifrance — Décret n°2023-259](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047422489) : TRI >10 ans = exemption art. R175-6 | **290/70 kW, TRI >10 ans** | Sources primaires Légifrance |

**Impact repo** : `regs.yaml:66` indique 2027 → **FAUX** (commentaire inversé). `compliance_engine.py:53` et `regulations/bacs/v2.yaml:12` indiquent 2030 → **CORRECTS**.

### Décret Tertiaire

| Point | Source 1 (primaire) | Source 2 | Retenue | Raison |
| --- | --- | --- | --- | --- |
| Seuil assujettissement | [Légifrance — Art. R174-22 CCH](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043819501) : "surface de plancher ≥ 1000 m²" | [Ministère Écologie — EET](https://www.ecologie.gouv.fr/politiques-publiques/eco-energie-tertiaire-eet) : confirme 1000 m² | **1000 m²** | Source primaire Légifrance |
| Trajectoire réduction | [Légifrance — Art. L174-1 CCH](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043977483) : -40% 2030, -50% 2040, -60% 2050 | [Ministère Écologie — EET](https://www.ecologie.gouv.fr/politiques-publiques/eco-energie-tertiaire-eet) : mêmes objectifs | **-40/-50/-60%** | Source primaire Légifrance |
| Sanctions | [Opera Énergie](https://opera-energie.com/sanctions-decret-tertiaire/) : 750€ PP / 3750€ PM (non-déclaration), 1500€ PP / 7500€ PM (non-plan), 1750€/1000m², name-and-shame | [le-decret-tertiaire.fr](https://www.le-decret-tertiaire.fr/sanction-decret-tertiaire/) : confirme mêmes montants | **7500€ PM max (non-plan)** | 2 sources secondaires concordantes. Pas de source Légifrance directe trouvée sur le montant. Grille de sanctions nuancée (pas un flat 7500€) |

**Impact repo** : `BASE_PENALTY_EURO = 7_500` → **SIMPLIFICATION ACCEPTABLE** mais le label devrait préciser "amende maximale personne morale (non-mise en œuvre du plan d'actions)".

### APER — Solarisation parkings et toitures

| Point | Source 1 (primaire) | Source 2 | Retenue | Raison |
| --- | --- | --- | --- | --- |
| Seuil parking | [Légifrance — Art. 40 Loi n°2023-175](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000047294291) : parking ≥ 1500m², ombrières ENR ≥ 50% surface | [Ministère Écologie — Guide parcs stationnement](https://www.ecologie.gouv.fr/sites/default/files/documents/Guide-parcs-de-stationnement-WEB.pdf) : confirme | **≥ 1500m², ≥ 50% couverture** | Source primaire Légifrance |
| Deadlines parking | [Légifrance — Art. 40 Loi n°2023-175](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000047294291) : ≥10000m² → 01/07/2026, 1500-10000m² → 01/07/2028 | [Légifrance — Décret n°2024-1023](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050495478) : application art. 40 | **2026-07 / 2028-07** | Sources primaires Légifrance ×2 |
| Toiture 500m² | **ATTENTION** : L'obligation toitures vient de l'art. L171-4 CCH + arrêté 19/12/2023, pas directement de la loi APER (art. 40 qui concerne les parkings) | [Légifrance — Arrêté 19/12/2023](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000048707438) : proportion toiture couverte | **Simplification POC** | Le seuil 500m² et deadline 2028-01-01 dans le repo sont des approximations. L'obligation réelle dépend du type de bâtiment (neuf/rénovation lourde) |

**Impact repo** : Parkings → **CORRECT**. Toitures → **SIMPLIFICATION** (la distinction art. 40 APER vs. art. L171-4 CCH devrait être documentée).

### TURPE 7

| Point | Source 1 (primaire) | Source 2 | Retenue | Raison |
| --- | --- | --- | --- | --- |
| Référence tarifaire | [Légifrance — Délibération CRE n°2025-78](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195) du 13/03/2025, JO 14/05/2025 | [Enedis — Grilles tarifaires TURPE 7](https://www.enedis.fr/media/4717/download) au 01/08/2025 | **CRE n°2025-78, en vigueur 01/08/2025** | Sources primaires CRE + Enedis |

**Impact repo** : `billing_engine/catalog.py` cite "CRE TURPE 7 BT>36kVA" → **SOURCE CORRECTE**.

### Scoring — 5 frameworks

| Framework | Texte officiel | Évaluateur repo | Statut |
| --- | --- | --- | --- |
| Décret Tertiaire | Art. L174-1 / R174-22 CCH (décret n°2019-771) | IMPLÉMENTÉ | ✅ |
| BACS | Art. R175-1 à R175-6 CCH (décret n°2020-887, modifié 2023, 2025) | IMPLÉMENTÉ | ✅ |
| APER | Loi n°2023-175 art. 40 + décret n°2024-1023 | IMPLÉMENTÉ (éligibilité + RegOps rules) | ✅ |
| DPE Tertiaire | Arrêtés 2024 modifiant arrêté 15/09/2006 | NON IMPLÉMENTÉ | ⚠️ Réglementairement pertinent, à implémenter |
| CSRD | Directive 2022/2464, ordonnance FR 2023-1142 | NON IMPLÉMENTÉ | ⚠️ Réglementairement pertinent, à implémenter |

**Arbitrage** : Les 5 obligations existent réellement. Le score A.2 exclut correctement les non-évalués du dénominateur (pas d'impact sur le chiffre affiché).

---

## Audits détaillés

| Étape | Fichier | Contenu |
| --- | --- | --- |
| 0 — Cadrage | `docs/audits/AUDIT_PROMEOS_ETAPE_00_CADRAGE_2026-03-23.md` | Baseline, périmètre, cartographie, conventions |
| 1 — Fil conducteur | `docs/audits/AUDIT_PROMEOS_ETAPE_01_FIL_CONDUCTEUR_2026-03-23.md` | Trace code-path complète patrimoine→actions |
| 2 — Règles métier | `docs/audits/AUDIT_PROMEOS_ETAPE_02_REGLES_METIER_CONFORMITE_2026-03-23.md` | Formules, seuils, deadlines, scoring, preuves |

*Audit consolidé le 2026-03-23 sur le repo `c:\Users\amine\promeos-poc\promeos-poc`. Sources vérifiées ×2 minimum le 2026-03-23.*
