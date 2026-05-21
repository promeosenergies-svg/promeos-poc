# PROMEOS — Note produit et stratégique actualisée

> **Date** : 21 mai 2026
> **Version** : 3.0 (actualisation post-Sprint F / V1.2 Usages)
> **Statut** : Document stratégique de référence — remplace les notes de version 2.x d'avril 2026
> **Périmètre** : Synthèse 360° produit, marché, exécution et risques — à destination COMEX / pilote ETI / partenaires
> **Filiation** : Reprend et actualise `PROMEOS_STRATEGIE_FOURNISSEUR_4.0.md` (avril 2026), `ROADMAP_DOMINATION_PROMEOS.md` (mars 2026), `PLAN_EXECUTION_90J.md` (mars 2026), `ROADMAP_POST_AUDIT_2026Q2.md` (avril 2026)

---

## 1. Résumé exécutif

### Le pitch en une phrase

> **PROMEOS est le cockpit énergie B2B France qui transforme les obligations réglementaires, les factures et les courbes de charge en décisions opposables — sans jamais vendre un kWh.**

### Positionnement

**« Fournisseur 4.0 sans la fourniture »** : toute l'intelligence d'un fournisseur d'énergie nouvelle génération (analyse, optimisation, conformité, achat) avec une neutralité totale vis-à-vis du kWh. Cette indépendance est notre premier moat commercial : DAF et directions immobilières achètent une recommandation alignée sur leurs intérêts, pas sur ceux d'un fournisseur.

### Où nous en sommes (mai 2026)

| Dimension | État | Commentaire |
|---|---|---|
| Plateforme backend | 379 endpoints, 98 modèles SQLAlchemy, 4 moteurs réglementaires YAML versionnés | Stable |
| Plateforme frontend | 55+ pages React 18, navigation Simple/Expert, CommandPalette, Evidence Drawer | Stable |
| Couverture réglementaire | Décret Tertiaire, BACS, APER, CEE P6, Audit énergétique | 4 cadres en production |
| Brique Conformité | Score unifié pondéré, findings, dossier opposable, audit trail | V1.1+ board-ready |
| Brique Billing | Shadow billing TURPE 7, accise, CTA, TVA, 14 règles d'anomalie, reconciliation 3 voies | Stable Lockdown V2 |
| Brique Achat | 4 stratégies (Fixe / Indexé / Spot / Tarif Heures Solaires), Assistant 8 étapes | V2 + Audit |
| Brique Usages | Heatmap 7×24, profil journée, behavior_score, ScheduleEditor inline | V1.2 |
| Connecteurs réels | RTE eCO2mix + PVGIS opérationnels ; Enedis SGE (R6X, C68) en pipeline raw → fonctionnel | Phase SF6 en cours |
| Tests automatisés | 5 587 frontend + 841 backend + 142 E2E Playwright | DEMO SAFE SANS RÉSERVE |
| Mode démo | HELIOS 5 sites + MERIDIAN 3 sites, 730 j horaire + 365 j 15-min + météo réaliste | Déterministe RNG=42 |

### Les 3 verrous stratégiques

1. **Wedge primaire — Conformité opposable** : la seule plateforme qui va de l'assujettissement à la preuve PDF signée, en passant par l'action, avec traçabilité complète (rule_id, engine_version, base légale, hash SHA-256 des preuves).
2. **Wedge secondaire — Bill Intelligence explicable** : décodage facture composante par composante (TURPE 7 / accise / CTA / TVA) avec attribution de chaque anomalie à sa cause et son ROI estimé.
3. **Wedge long terme — Cockpit décisionnel énergie-patrimoine** : la chaîne unique `patrimoine → obligation → finding → action → preuve → impact €` reliant les 6 piliers HELIOS (EMS, RegOps, Bill, Achat, Flex, CX).

---

## 2. Contexte de marché — actualisé 2026

### Les 5 forces structurelles toujours actives

1. **Post-ARENH** : disparition au 31/12/2025, remplacement par VNU (prélèvement État 50 % > 78 €/MWh, 90 % > 110 €/MWh) et CAPN. Contrats moyen terme EDF post-ARENH ~60 €/MWh, enchères Y+4/Y+5 entre 66 et 72 €/MWh. Volatilité B2B durablement plus élevée qu'en monde ARENH.
2. **Réglementation cumulative** :
   - Décret Tertiaire — jalon **−40 % en 2030** désormais à 4 ans, déclaration OPERAT annuelle, sanctions jusqu'à 7 500 €/site.
   - BACS — seuil **70 kW dès 2030** (décret 2025-1343), seuil 290 kW déjà en vigueur depuis 01/01/2025.
   - **Audit énergétique** (loi 2025-391) — deadline **11/10/2026** pour conso > 2.75 GWh ; SMÉ ISO 50001 deadline 11/10/2027 pour conso > 23.6 GWh.
   - APER — toitures PV obligatoires bâtiments existants > 500 m² **dès janvier 2028**, parkings > 1 500 m² progressif depuis juillet 2023.
   - CSRD post-Omnibus, CBAM, ETS2 (2028), e-facture (01/09/2026), capacité RTE (01/11/2026).
3. **Disponibilité des données** : Linky/Gazpar à >95 % de pénétration, API Enedis SGE / DataConnect / GRDF ADICT matures, mais consentement RGPD et parsing des flux R6X / C68 / R171 restent un mur technique pour 80 % du marché.
4. **Outillage SaaS sous-pénétré** : <5 % des 100 000 entreprises multi-sites cibles ont aujourd'hui un outil dédié énergie. Les solutions historiques sont soit des modules ERP/CAFM (trop génériques), soit des outils mono-cadre (OPERAT only, BACS only).
5. **Pression DAF** : la facture énergie est désormais un poste >2 % du CA pour la moitié des PME tertiaires, et il faut désormais l'expliquer en COMEX.

### Taille de marché (rappel)

| Indicateur | Valeur |
|---|---|
| Sites B2B France (électricité) | 5,39 M sites non résidentiels (261 TWh) |
| Cible primaire C2-C5 multi-sites | ~100 000 entreprises |
| Dépense énergie annuelle B2B France | ~60 Md€ |
| Pénétration outils dédiés | <5 % |
| SAM PROMEOS | ~500 M€ |
| SOM année 3 | ~5 M€ |

### Tendance émergente 2026 — la « preuve opposable »

La sanction du décret tertiaire n'est plus théorique : la première vague de mises en demeure publiques OPERAT est attendue sur l'exercice 2026. Le besoin n'est plus de « savoir » qu'on est non conforme, mais de prouver qu'on agit. C'est exactement le terrain de PROMEOS.

---

## 3. Cartographie des acteurs — positionnement PROMEOS

| Catégorie | Acteur type | Force | Faiblesse | Position PROMEOS |
|---|---|---|---|---|
| Fournisseur historique | EDF Pro, Engie Pro | Données contractuelles, force commerciale | Conflit d'intérêt sur la recommandation | **Complémentaire** : on lit leur facture |
| Fournisseur alternatif | TotalEnergies, Alpiq, Plüm | Pricing post-ARENH, marketplace | Faible pilotage conformité | **Complémentaire** : on outille leur churn |
| GRD / GRT | Enedis, GRDF, RTE | Données brutes, API officielles | Pas d'UX décideur, pas de réglementaire | **Consommateur** : SGE, ADICT, eCO2mix |
| Éditeurs SaaS énergie | Deepki, Greenly, Carbon Maps, Sami | UX moderne, story carbone | Pas de moteur réglementaire opposable, pas de shadow billing | **Concurrent direct** sur conformité — différenciation par chaîne preuve opposable |
| Courtier énergie | Opera Énergie, Capitole | Carnet d'adresses fournisseurs, expertise contractuelle | Pas de SaaS récurrent, modèle commission | **Partenaire / canal** : ils revendent PROMEOS |
| Agrégateur flex | Voltalis, Smart Grid Energy | Capacité physique sur la flexibilité | Pas de gestion patrimoine | **Aval Pilier 5 Flex** |
| Producteur EnR / ESCo | Engie Solutions, Idex, Dalkia | Travaux + financement | Pas de cockpit transverse | **Amont** : ils consomment nos diagnostics |

**Notre angle unique** : aucun de ces acteurs ne tient à la fois la chaîne `patrimoine → conformité opposable → bill intelligence shadow → stratégie achat post-ARENH` avec neutralité fournisseur.

---

## 4. Proposition de valeur — les 6 piliers HELIOS

PROMEOS s'organise en 6 piliers fonctionnels articulés autour d'un modèle de données unique `Organisation → Entité Juridique → Portefeuille → Site → Bâtiment → Compteur → Delivery Point`.

| Pilier | Module produit | Promesse client | Différenciant |
|---|---|---|---|
| **EMS** | Conso & Usages, Monitoring V2, Carpet plot, signature énergétique, CUSUM, profil 7×24, behavior_score | « Comprenez vos courbes » | Heatmap 7×24 + ScheduleEditor inline + behavior_score 0-100 |
| **RegOps** | Conformité Décret Tertiaire, BACS, APER, Audit énergétique, OPERAT, dossier PDF opposable | « Prouvez votre conformité » | Moteur YAML versionné + coffre de preuves persisté + dossier comité |
| **Bill** | Bill Intelligence shadow billing, 14 règles d'anomalie, reconciliation 3 voies, contrats radar, déductions accise | « Lisez chaque ligne de facture » | TURPE 7 native + segment C4/C5 dynamique + fallback flag + explicabilité top 3 contributeurs |
| **Achat** | 4 stratégies (Fixe, Indexé, Spot, THS), Assistant 8 étapes, Offer Pricing, 6 offres demo, marketplace pricing | « Décidez votre stratégie post-ARENH » | Tarif Heures Solaires natif + scope lock + confidence cap medium + scénarios DAF-readable |
| **Flex** | Flex Foundations, NEBCO, signaux EcoWatt / Tempo, agrégateurs (cible Q4 2026) | « Valorisez votre flexibilité » | Cross-link avec EMS + scoring potentiel flex |
| **CX** | Notifications & Digest, IAM (11 rôles, JWT, impersonation), CommandPalette, Onboarding 6 étapes | « Distribuez à toute l'entreprise » | Multi-org (MERIDIAN), simple/expert mode, evidence-required workflow |

### Personas cibles — actualisation 2026

| Persona | Douleur n°1 | Ce que PROMEOS lui livre |
|---|---|---|
| **DAF / Contrôle de gestion** | Comprendre 30 composantes de facture × N sites × 12 mois | Cockpit € + variation N/N-1 + watchlist anomalies + dossier comité PDF |
| **Directeur immobilier** | Échéances Décret Tertiaire 2030 + BACS 2030 + APER 2028 | Timeline réglementaire visuelle + notifications J-90/J-30/J-0 + coffre preuves |
| **Responsable énergie** | Identifier les vraies anomalies parmi 200 alertes | Behavior_score + signature énergétique + ScheduleEditor inline |
| **Acheteur énergie** | Choisir stratégie post-ARENH sans data ni temps | Assistant Achat 8 étapes + 6 offres demo + confidence badges + bar chart coûts |
| **Resp. conformité / RSE** | Produire un dossier opposable sur 4 cadres réglementaires | Findings → actions → preuves → PDF avec engine_version + hash + base légale |
| **DSI / Admin** | RGPD, org-scoping, gestion droits | 11 rôles + scopes hiérarchiques + audit trail + connecteurs maîtrisés |

---

## 5. Architecture produit — état mai 2026

### Stack technique

| Couche | Technologie | Statut |
|---|---|---|
| Frontend | React 18 + Vite 5 + Tailwind v4 + Recharts 3 + Lucide | Stable |
| Backend | FastAPI 0.104 + Uvicorn + SQLAlchemy 2.0 + Pydantic 2.5 | Stable |
| DB applicative | SQLite `promeos.db` (PostgreSQL-ready via DATABASE_URL + Alembic) | POC SQLite, prod-ready Postgres |
| DB flux bruts | SQLite `flux_data.db` (séparée pour isolation Enedis SGE) | Validé SGE 4.5 + 5 |
| DB Knowledge Base | SQLite + FTS5 `kb.db` (12 items YAML) | Stable |
| Tests | pytest 7.4 + Vitest 4.0 + Playwright | 5 587 FE + 841 BE + 142 E2E |
| Ports | Backend :8001, Frontend :5173 (proxy `/api/*`) | Convention figée |
| Auth | JWT + 11 rôles + scopes hiérarchiques + impersonation | Production-ready (mode démo désactivable) |

### Sources de vérité canoniques (non négociables)

| Domaine | Fichier source unique | Garde-fou |
|---|---|---|
| Consommation | `backend/services/consumption_unified_service.py` | Source unique |
| Scoring conformité | `backend/regops/scoring.py` → `RegAssessment.compliance_score` | Poids externalisés YAML |
| Facteurs CO₂ | `backend/config/emission_factors.py` (ADEME V23.6 : 0.052 élec, 0.227 gaz) | Wrapper `emission_factors` skill |
| Résolution NAF | `backend/utils/naf_resolver.py:resolve_naf_code()` | Canonical |
| Tarifs réglementés | `backend/config/tarifs_reglementaires.yaml` | Versionné, ParameterStore |
| Seed démo | `backend/services/demo_seed/orchestrator.py` (RNG=42, déterministe) | Pack HELIOS + MERIDIAN |

### Règle d'or — zéro calcul métier en frontend

Tout calcul (CO₂, scoring, pénalité DT, prix fallback, IPE, réduction %) vit dans le backend, exposé via REST. Le frontend est affichage uniquement. Cette règle est protégée par des **source-guard tests pytest** (catégorie de test dédiée `tests/source_guards/`).

### Connecteurs

| Connecteur | État | Cadence | Échéance prod |
|---|---|---|---|
| RTE eCO2mix | Opérationnel (API publique sans clé) | Live | Livré |
| PVGIS | Opérationnel (API publique sans clé) | Live | Livré |
| Enedis SGE — raw R4x/R171/R50/R151/R63/R64/C68 | Pipeline validé SF1→SF5, isolé `flux_data.db` | Sur demande | SF6 raw→fonctionnel en cours |
| Enedis DataConnect OAuth2 PKCE (C5) | Stub | 30 min | Q3 2026 |
| GRDF ADICT REST | Stub | Quotidien | Q3 2026 |
| Météo-France | Stub + AR(1) synthèse | Quotidien | Q3 2026 |

---

## 6. Modèle économique — actualisation

### Pricing (rappel)

| Brique | Plan Essentiel | Plan Pro | Plan Entreprise |
|---|---|---|---|
| Par site / mois | 30-50 € | 80-120 € | sur devis |
| RegOps inclus | DT seul | DT + BACS + APER | + Audit énergétique + SMÉ ISO 50001 |
| Bill Intelligence | Lecture facture | Shadow billing + 14 anomalies | + reclaim assisté |
| Achat | Scénarios statiques | 4 stratégies + Assistant | + marketplace offres |
| Connecteurs | Manuels CSV/PDF | Enedis DataConnect | + GRDF ADICT + SGE SOAP |
| Coffre de preuves | 1 Go | 10 Go | illimité |
| Multi-org | 1 org | 3 orgs | illimité |

### Unit economics cibles (année 3)

| Indicateur | Cible |
|---|---|
| ARR par client moyen | 25-40 k€ |
| Coût acquisition (CAC) | <15 k€ |
| Payback CAC | <12 mois |
| Marge brute | >75 % |
| Net Revenue Retention | >110 % |

### Hypothèses de croissance

- **Année 1** (S2 2026) : 3-5 pilotes ETI (~50-100 sites), ARR ~200 k€.
- **Année 2** : 25-40 clients (~1 000-2 000 sites), ARR ~1,5-2 M€.
- **Année 3** : 100+ clients (~5 000+ sites), ARR ~5 M€.

---

## 7. Verdict produit mai 2026 — ce que nous possédons, ce qui manque

### FAITS — Capacités déjà productives

| Capacité | Niveau | Rareté marché |
|---|---|---|
| 4 cadres réglementaires (DT + BACS + APER + Audit) | Fonctionnel | Très rare |
| Moteur YAML versionné avec assujettissement explicable (`rule_id`, `engine_version`, base légale) | Solide | Unique |
| Score conformité unifié pondéré, poids externalisés YAML | Solide | Unique |
| Workflow findings → actions → preuves → close gate | Solide | Différenciant |
| Shadow billing TURPE 7 + accise + CTA + TVA + 14 règles d'anomalie | Avancé | Très différenciant |
| Reconciliation 3 voies (compteur ↔ facture ↔ contrat) avec 1-click fix + audit trail | Avancé | Unique |
| Assistant Achat 8 étapes + 6 offres demo + Tarif Heures Solaires natif | Avancé | Différenciant |
| Behavior_score 0-100 + ScheduleEditor inline + signature énergétique | Avancé | Très rare en SaaS |
| Multi-org (MERIDIAN), scopes hiérarchiques, 11 rôles, impersonation | Production | Rare |
| Evidence Drawer « Pourquoi ce chiffre ? » sur Cockpit + Explorer | Solide | Unique |
| Source-guards pytest interdisant calcul métier frontend | Solide | Garde-fou rare |
| 5 587 tests FE + 841 BE + 142 E2E, déterministe | DEMO SAFE | Fondation fiable |

### Ce qui reste à verrouiller

| Gap | Sévérité | Impact business |
|---|---|---|
| Coffre de preuves persisté (V0 état React → API blob + hash) | **Critique** | Bloque l'opposabilité du dossier |
| Export dossier comité PDF opposable (WeasyPrint) | **Critique** | Bloque la monétisation et la story de vente |
| Notifications échéances proactives (J-90/J-30/J-0) | **Fort** | Bloque la rétention |
| Benchmark sectoriel V0 (ADEME/CEREN, P25/médiane/P75) | **Fort** | Bloque la crédibilité DG |
| Projection DT 2030 / 2040 visible en UI | **Fort** | Bloque le narratif long terme |
| Endpoints sans org-scoping (≈43 restants : power, contracts_v2, flex, usages) | **Critique** | Bloque mise en prod multi-tenant |
| Couverture tests : 25 % → 60 % | **Moyen** | Risque régression sur volumétrie réelle |
| Connecteurs Enedis SGE SF6 raw→fonctionnel | **Fort** | Bloque l'autonomie data au-delà de la démo |
| Performance pages > 2 s sur volumétries clients réels | **Moyen** | UX dégradée hors démo |

### HYPOTHÈSES — Ce qui peut devenir moat

1. **Le coffre de preuves persisté + versionné** devient le verrou d'adoption : une fois les preuves dans PROMEOS, le client ne migre plus.
2. **Le moteur YAML réglementaire** est cumulatif : chaque jurisprudence et arrêté modélisé enrichit un patrimoine fork-proof.
3. **Le shadow billing TURPE 7** lié au patrimoine est un angle unique conformité × facturation que personne ne tient bout à bout.
4. **Le benchmark sectoriel V0** (médiane par usage × zone climat × surface) crédibilise le score auprès des DG et justifie un pricing premium.
5. **L'intégration conformité → conso réelle → impact facture** est le vrai différenciant cockpit : aucun outil ne sait chiffrer « votre non-conformité BACS vous coûte X €/an ».

---

## 8. Stratégie 12 mois — 4 horizons

### H1 — 0 à 30 jours (juin 2026) : « Coffre & Dossier »

> **Objectif** : Rendre PROMEOS opposable.

| Initiative | Livrable | Preuve de succès |
|---|---|---|
| Coffre de preuves persisté | Modèle `ProofFile` (blob + hash SHA-256), API upload/list/delete, frontend remplace state React par API | Upload → F5 → toujours présent |
| Export dossier comité PDF | WeasyPrint / wkhtmltopdf, endpoint `GET /compliance/dossier/{org_id}/pdf` (score + obligations + findings + preuves jointes + signature date) | PDF téléchargeable avec preuves jointes |
| Notifications échéances | Cron hebdo, J-90/J-30/J-0 par obligation, digest email opt-in | Email reçu « Échéance BACS dans 30 jours » |
| Sprint A sécurité — org-scoping résiduel | `resolve_org_id` sur les 43 endpoints restants, 20+ tests cross-org isolation | Aucun endpoint sans `Site.org_id` |

### H2 — 31 à 90 jours (juillet-août 2026) : « Benchmark & Trajectoire »

> **Objectif** : Crédibiliser face aux experts et au comité.

- Benchmark sectoriel V0 — données ADEME / CEREN, endpoint `/api/benchmark`, widget « vs médiane par archétype NAF × surface × zone climat ».
- Projection DT 2030 / 2040 / 2050 — sparkline trajectoire dans obligation Décret Tertiaire, simulation « si j'agis ».
- Lien conformité → conso réelle — widget `kWh/m²/an` dans obligation DT, lien vers `/consommations`.
- APER calcul puissance crête estimée (kWc/m² toiture) + coût + ROI simplifié.

### H3 — 91 à 180 jours (Q4 2026) : « Connecteurs réels & Pilote »

> **Objectif** : Passer de démo à données réelles chez un pilote ETI.

- SF6 promotion raw → fonctionnel : `meter_load_curve`, `meter_energy_index`, `meter_power_peak` dans `promeos.db`.
- Enedis DataConnect OAuth2 PKCE (C5, cadence 30 min) + lifecycle consentements RGPD.
- GRDF ADICT REST.
- Premier pilote ETI : connecteur réel + demo scenario complet + rapport PDF automatisé multi-module.

### H4 — 181 à 365 jours (S1 2027) : « Multi-tenant & Échelle »

> **Objectif** : Passer de pilote à 25 clients payants.

- EMS Tier 2 : drill-down portefeuille > site > bâtiment > compteur, anomalie ML (LOF + IsolationForest + SHAP).
- Achat V2 : Mode Express, marketplace offres réelles, extension Gaz.
- Marketplace connecteurs (post-coffre de preuves).
- Performance < 1,5 s toutes pages.
- 25 clients payants, ARR ~1,5 M€.

---

## 9. Go-to-market — actualisation

### Segmentation client cible (S2 2026)

| Segment | Description | Pourquoi PROMEOS | Pricing cible |
|---|---|---|---|
| **ETI tertiaire multi-sites** (cible primaire) | 10-50 sites, 250-2 500 salariés, secteur retail / banque / assurance / santé | Décret Tertiaire 2030 imminent + audit énergétique 11/10/2026 | 30-80 k€ ARR |
| **Foncières / asset managers** | 50-500 actifs, Article 29 LEC + CSRD | Reporting opposable + benchmark + dossier comité | 80-300 k€ ARR |
| **Grands comptes industrie** | >2,75 GWh, obligation audit + ISO 50001 | Bill Intelligence + flex + post-ARENH | 100-500 k€ ARR |

### Canal de distribution

- **Vente directe Account Executive** sur top 100 ETI tertiaire (DAF + direction immobilière).
- **Co-vente avec courtiers énergie** (Opera Énergie, Capitole) — PROMEOS comme « outil de pilotage » dans la proposition globale du courtier.
- **Partenariat avec cabinets d'audit énergétique** — PROMEOS comme livrable opposable post-audit.
- **Partenariat avec ESCo / Engie Solutions / Idex / Dalkia** — PROMEOS comme cockpit de suivi post-travaux.

### Partenariats stratégiques prioritaires

| Partenaire | Apport | Statut |
|---|---|---|
| Cabinet d'audit énergétique (3-5 cibles) | Lead pré-qualifiés, crédibilité expert | À engager Q3 2026 |
| Courtier énergie majeur (1-2 cibles) | Lead acheteur, négociation offres | À engager Q3 2026 |
| ADEME / OPERAT | Source officielle benchmark | Données publiques utilisées (disclaimer) |
| Enedis / GRDF (partenariat API) | Stabilité connecteurs + visibilité | Pipeline Q4 2026 |

---

## 10. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Sprint sécurité org-scoping > 2 sprints | Moyenne | Pipeline prod bloqué | Décomposition par module (power.py d'abord) |
| Connecteurs Enedis / GRDF instables en prod | Haute | Données réelles bloquées | Circuit breaker + retry + monitoring + gap detection |
| Performance dégradée sur volumétries clients réels (1 000+ sites) | Moyenne | UX dégradée | Load test k6 dès Sprint 10, indexes BD, Redis cache |
| Pilote client repoussé S2 2026 → S1 2027 | Faible | Impact business modéré | Demo interne mensuelle, pipeline avec 3 prospects en parallèle |
| Concurrent SaaS européen lance la conformité opposable | Moyenne | Différenciation érodée | Verrouillage coffre de preuves + benchmark + moteur YAML cumulatif (S1 2026) |
| Décret BACS reporté ou allégé | Faible | Moins de pression vente | Wedge primaire toujours valide via DT + audit énergétique |
| Volatilité prix post-ARENH > attentes | Faible | Achat moins prédictible | Stratégie Spot et THS déjà natives |
| RGPD / consentement DataConnect contesté | Faible | Connecteur Enedis ralenti | Lifecycle consentements documenté, mode CSV fallback |

---

## 11. Métriques de succès — boussole pilote

### KPIs produit (cibles à 90 jours)

| KPI | Baseline mai 2026 | Cible août 2026 |
|---|---|---|
| Preuves persistées par obligation | 0 (état React) | >2 par obligation active |
| PDF dossier comité générés | 0 | >5 par client pilote |
| Actions compliance créées via finding | ~12 dans seed | >30 par client pilote |
| Score conformité moyen pilote | 62/100 cible audit | >75/100 |
| Endpoints org-scopés | ~60 % | 100 % |
| Couverture tests | 25 % | 60 % |
| Temps chargement pages | ~3 s | <2 s |

### KPIs business (cibles 12 mois)

| KPI | S2 2026 | S1 2027 |
|---|---|---|
| Clients payants | 3-5 pilotes | 25-40 |
| ARR | 200 k€ | 1,5-2 M€ |
| Sites couverts | 50-100 | 1 000-2 000 |
| Net Revenue Retention | n/a | >110 % |
| CAC payback | n/a | <12 mois |

---

## 12. Gouvernance et exécution

### Règles non négociables (extrait `SKILL.md` / `CLAUDE.md`)

1. **Zéro calcul métier en frontend** — garde-fou pytest source-guards.
2. **Org-scoping obligatoire** via `resolve_org_id` sur chaque endpoint.
3. **Atomic commits** : `fix(module-pN): Phase X.Y — description`.
4. **Sources de vérité uniques** : `consumption_unified_service.py`, `regops/scoring.py`, `naf_resolver.py`, `emission_factors.py`, `tarifs_reglementaires.yaml`.
5. **Baseline tests jamais régresser** : FE ≥ 3 783, BE ≥ 843 (cibles V88) — actualisées à 5 587 FE / 841 BE / 142 E2E.
6. **Branche** `claude/*` — jamais commit direct main.
7. **Workflow** : Phase 0 read-only → STOP gate → phases numérotées → DoD → atomic commit → source-guard test.

### Pilotage 90 jours

- **Baseline figée** — aucun ajout de scope avant G2.
- **Buffer 12 %** sur S4-S10 (4 demi-journées).
- **Benchmark V0** = ADEME / CEREN + disclaimer obligatoire.
- **Cadence vendredi** : 1 tableau de bord, 1 preuve, 1 décision.
- **Audit Patrimoine** briefé, lancement post-G2.

### Organisation actuelle

- 1,5 ETP produit + dev.
- Pile d'agents IA dédiés (architect-helios, implementer, code-reviewer, qa-guardian, regulatory-expert, bill-intelligence, ems-expert, data-connector, security-auditor, test-engineer, prompt-architect) — orchestration via Claude Code.

---

## 13. Conclusion — ce que cette note dit en une page

PROMEOS a franchi le cap du POC. Plateforme stable, 4 cadres réglementaires en production, shadow billing TURPE 7, Assistant Achat post-ARENH, 5 587 tests verts, démo HELIOS + MERIDIAN canonique.

Le marché est en train de basculer : audit énergétique 11/10/2026, BACS 70 kW en 2030, Décret Tertiaire à 4 ans, première vague de mises en demeure OPERAT. La demande passe de « savoir » à « prouver ».

Notre **wedge primaire** est la **conformité opposable** : la chaîne `patrimoine → finding → action → preuve → PDF` que personne ne tient bout à bout avec neutralité fournisseur.

**Les 4 paris des 90 prochains jours** :
1. **Coffre de preuves persisté** — verrou d'adoption.
2. **Dossier comité PDF** — monétisation.
3. **Notifications échéances** — rétention.
4. **Benchmark sectoriel V0** — crédibilité DG.

Ce qui transformera PROMEOS de cockpit en plateforme : le coffre, le PDF, et le pilote.

> **Le vrai gap n'est plus technique. C'est le passage de « dashboard qui montre » à « plateforme qui prouve et qui fait agir ».**

---

## Annexes — références internes

| Document | Filiation |
|---|---|
| `docs/PROMEOS_STRATEGIE_FOURNISSEUR_4.0.md` (avril 2026) | Stratégie fond marché — toujours valide |
| `docs/roadmaps/ROADMAP_DOMINATION_PROMEOS.md` (mars 2026) | Thèse domination 12 mois |
| `docs/roadmaps/PLAN_EXECUTION_90J.md` (mars 2026) | Plan 90 jours — baseline figée |
| `docs/roadmaps/PILOTAGE_EXECUTION_90J.md` (mars 2026) | Couche pilotage hebdo |
| `docs/ROADMAP_POST_AUDIT_2026Q2.md` (avril 2026) | Sprints sécurité + tests + connecteurs |
| `docs/product/V1_CONFORMITE_GEL_FINAL.md` | Gel conformité V1.1 |
| `docs/product/LOCKDOWN_BILLING_V2.md` | Lockdown billing V2 |
| `docs/product/BRIEF_USAGES_V1.3.md` | Brique Usages V1.2 → V1.3 |
| `SKILL.md`, `CLAUDE.md` | Règles non négociables |
| `README.md` (V117+ / V1.2) | État technique exhaustif |

---

*Note rédigée le 21 mai 2026 — à actualiser après G1 (mi-juillet 2026) et G2 (fin août 2026).*
