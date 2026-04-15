# AUDIT BACS + OPERAT — PROMEOS

> Date : 2026-03-15
> Auditeur : Claude Opus 4.6 (audit exhaustif repo)
> Perimetre : Conformite reglementaire, Data model, UX/UI, Architecture, Preuve/Audit-trail, Risques business
> Methode : Exploration systematique du repo (backend models, services, routes, tests, seeds, frontend pages, composants, labels)

---

# 1. VERDICT EXECUTIF

| Axe | Note /100 |
|-----|-----------|
| **Conformite BACS** | 55 |
| **Conformite OPERAT** | 35 |
| **Data model** | 60 |
| **UX/UI** | 50 |
| **Architecture** | 65 |
| **Preuve / Audit-trail** | 30 |
| **Note globale** | **45/100** |

**Verdict sans filtre :** PROMEOS a une architecture BACS solide (Putile, seuils, TRI, inspections) et un modele OPERAT/Tertiaire structurellement correct (EFA, batiments, responsabilites, preuves). Mais la brique est un POC avance, pas un produit de conformite. Il manque les fondamentaux qui font la difference entre "on affiche un score" et "on peut deposer un dossier defendable" : pas de consommation de reference, pas de trajectoire -40%/-50%/-60%, pas de normalisation climatique, pas d'audit-trail des preuves, pas de workflow d'approbation, pas de depot reel OPERAT. Un client qui se fie a PROMEOS pour sa conformite aujourd'hui prend un risque reel.

---

# 2. MATRICE DES EXIGENCES

## BACS

| Exigence | Statut | Risque | Preuve repo | Correction |
|----------|--------|--------|-------------|-----------|
| Seuils puissance 290/70 kW | OK | - | `bacs_engine.py:192-204` | - |
| Echeances 2025-01-01 / 2030-01-01 | OK | - | `regulations/bacs/v2.yaml` | - |
| Calcul Putile (cascade/reseau/indep) | OK | - | `bacs_engine.py:70-124` | - |
| Distinction chauffage/clim/ventilation | OK | - | `CvcSystemType enum` | - |
| Declenchement construction neuve | OK | - | `bacs_engine.py:168` | - |
| Declenchement renouvellement CVC | OK | - | `bacs_engine.py:177` | - |
| Exemption TRI > 10 ans | OK | - | `bacs_engine.py:220-276` | - |
| Periodicite inspection 5 ans | OK | - | `bacs_engine.py:285-327` | - |
| Classe A/B du systeme GTB | KO | Critique | Aucun champ `system_class` | Ajouter enum A/B/C/D a BacsCvcSystem |
| Zones fonctionnelles | KO | Majeur | Aucun modele BacsZone | Creer modele zone + rattachement |
| Detection perte efficacite | KO | Majeur | Aucun baseline performance | Ajouter baseline + seuil + alerte |
| Interoperabilite (BACnet/KNX/OPC) | KO | Moyen | Aucun champ interop | Ajouter enum interop_standard |
| Conservation donnees 5 ans | KO | Majeur | Aucune politique retention | Ajouter retention_until + cleanup |
| Pas horaire monitoring | KO | Majeur | Aucun modele performance horaire | Ajouter BacsPerformanceMetric |
| Formation exploitant | KO | Moyen | Aucun modele operateur | Ajouter BacsOperator + training |
| Rapport inspection detaille | PARTIEL | Majeur | BacsInspection.report_ref seul | Ajouter BacsInspectionFinding |
| Workflow approbation exemption | PARTIEL | Majeur | TRI calcule mais jamais approuve | Ajouter champs approved/expires |
| Penalite non-conformite | PARTIEL | Moyen | Hardcode 7500EUR L472 | Charger depuis regs.yaml |

## OPERAT / Decret Tertiaire

| Exigence | Statut | Risque | Preuve repo | Correction |
|----------|--------|--------|-------------|-----------|
| Seuil 1000 m2 tertiaires | OK | - | `tertiaire_service.py:172` | - |
| Structure EFA (CRUD) | OK | - | `tertiaire.py models + routes` | - |
| Rattachement batiments | OK | - | `TertiaireEfaBuilding` | - |
| Roles (proprietaire/locataire/mandataire) | OK | - | `TertiaireResponsibility` | - |
| Evenements perimetre | OK | - | `TertiairePerimeterEvent` | - |
| Systeme preuves documentaires | PARTIEL | Majeur | Catalogue ok, workflow manquant | Ajouter workflow validation |
| Export CSV format OPERAT | PARTIEL | Majeur | Structure ok, donnees incompletes | Ajouter conso reference + normalisation |
| Consommation annee de reference | KO | **Critique** | Aucun champ reference_year_kwh | Ajouter au modele EFA |
| Trajectoire -40%/-50%/-60% | KO | **Critique** | Calcule dans CSV, jamais valide | Implementer validation trajectoire |
| Normalisation climatique | KO | **Critique** | Aucun support NF/HDD/CDD | Creer modele climat + facteur |
| Dossier modulation | KO | Majeur | Evenement capture, workflow absent | Creer TertiaireModulationDossier |
| Depot reel OPERAT | KO | **Critique** | Simulation uniquement | Ajouter tracking depot + accuse |
| Multi-entites coordination | KO | Majeur | Detecte mais pas gere | Creer TertiaireEntityDeclaration |
| Historique declarations | KO | Majeur | Pas de versioning | Creer TertiaireDeclarationHistory |
| Batiment mixte (usage multiple) | KO | Moyen | usage_label = string unique | Supporter JSON multi-usage |
| Echeances 2030/2040/2050 | PARTIEL | Moyen | Hardcode dans CSV export | Tracker dynamiquement |

## Preuve / Audit-trail

| Exigence | Statut | Risque | Preuve repo | Correction |
|----------|--------|--------|-------------|-----------|
| Journal modifications preuves | KO | **Critique** | Aucun ProofEventLog | Creer modele + logger |
| Qui a saisi quoi, quand | PARTIEL | Majeur | ActionEvent ok, preuves non | Etendre a toutes les entites |
| Versionnage declarations | KO | Majeur | Pas d'historique | Creer DeclarationHistory |
| Export certifie (checksum/signature) | KO | **Critique** | Aucun checksum/signature | Ajouter hash + signature |
| Upload fichiers preuves | KO | Majeur | file_url en reference externe | Implementer upload multipart |
| Politique retention donnees | KO | Majeur | Aucun champ retention | Ajouter retention_until |
| Rapport conformite PDF signe | PARTIEL | Moyen | PDF existe, non signe | Ajouter signature numerique |

---

# 3. FAILS CRITIQUES

Par ordre de gravite :

| # | Fail | Gravite | Impact |
|---|------|---------|--------|
| **F1** | Aucune consommation de reference stockee par EFA → impossible de valider la trajectoire OPERAT | Critique | Reglementaire + Business |
| **F2** | Trajectoire -40%/-50%/-60% calculee dans le CSV mais jamais validee → le client ne sait pas s'il est conforme | Critique | Reglementaire |
| **F3** | Aucun audit-trail des changements de statut des preuves → indefendable en cas d'audit ADEME | Critique | Reglementaire + Juridique |
| **F4** | Depot OPERAT = simulation uniquement → le client pense avoir depose alors que non | Critique | Business (DANGEREUX) |
| **F5** | Aucune normalisation climatique → les consommations comparees sont biaisees | Critique | Reglementaire |
| **F6** | Classe A/B du systeme GTB non verifiee → BACS peut etre "conforme" avec un systeme classe C/D | Critique | Reglementaire |
| **F7** | Aucune detection de perte d'efficacite → exigence BACS fondamentale non couverte | Majeur | Reglementaire |
| **F8** | Export non certifie (pas de checksum/signature) → non recevable comme preuve | Majeur | Juridique |
| **F9** | Pas de zones fonctionnelles BACS → conformite partielle seulement | Majeur | Reglementaire |
| **F10** | Workflow approbation modulation absent → evenements perimetre sans suivi | Majeur | Reglementaire |

---

# 4. AUDIT DETAILLE

## 4.1 Reglementaire BACS

**Points forts :**
- Calcul Putile correct (cascade/reseau/independant, max chauffage/clim)
- Seuils 290/70 kW conformes au decret 2020-887
- Echeances 2025/2030 correctes avec chargement YAML
- TRI exemption > 10 ans implementee
- Inspection 5 ans avec suivi echeance
- 25+ tests unitaires couvrant les cas nominaux

**Points faibles critiques :**
- Aucune verification de classe A/B du systeme (EN 15232)
- Pas de zones fonctionnelles (article L. 174-1)
- Pas de suivi performance horaire (exigence BACS)
- Pas de detection baseline/degradation
- Pas d'interoperabilite (BACnet/KNX/OPC UA)
- Pas de formation/competence exploitant
- Penalite 7500 EUR hardcodee au lieu de chargee depuis config
- Findings inspection sans details (defauts, actions correctives)
- Score conformite trop simpliste (0-100 sans granularite)

**Fichiers audites :** `bacs_models.py`, `bacs_engine.py`, `bacs.py (routes)`, `compliance_engine.py`, `compliance_rules.py`, `bacs_ops_monitor.py`, `test_bacs_engine.py`, `gen_bacs.py`

## 4.2 Reglementaire OPERAT

**Points forts :**
- Structure EFA complete (batiments, responsabilites, evenements, preuves, liens)
- Seuil 1000 m2 correctement applique
- Controles qualite donnees (8 regles)
- Catalogue preuves structure (6 types)
- Export CSV format compatible OPERAT
- Pre-verification avant export

**Points faibles critiques :**
- **AUCUNE consommation de reference** stockee dans le modele EFA
- **AUCUNE validation trajectoire** (-40% 2030, -50% 2040, -60% 2050)
- **AUCUNE normalisation climatique** (NF EN ISO 51-732)
- **Depot = simulation** (label explicite "SUBMITTED_SIMULATED")
- Pas d'annee de reference verrouillable
- Pas de workflow modulation (evenements captures mais pas approuves)
- Pas de multi-entites coordination
- Pas d'historique declarations
- CSV export calcule les objectifs depuis Site.annual_kwh_total (source non verifiee)
- Pas de distinction conso elec/gaz/reseau dans le modele EFA

**Fichiers audites :** `tertiaire.py (models)`, `tertiaire_service.py`, `tertiaire.py (routes)`, `operat_export_service.py`, `tertiaire_proofs.py`, `tertiaire_proof_catalog.py`, `compliance_rules.py`

## 4.3 Modele de donnees

**Couverture :**
```
Organisation > EntiteJuridique > Portefeuille > Site > Batiment > Compteur
                                                  > BacsAsset > BacsCvcSystem
                                                  > TertiaireEfa > TertiaireEfaBuilding
                                                                 > TertiaireResponsibility
                                                                 > TertiaireDeclaration
                                                                 > TertiaireProofArtifact
```

**Manque dans la chaine :**
- Zone fonctionnelle (entre Batiment et Systeme)
- Consommation par EFA (entre EFA et Declaration)
- Donnees climatiques (rattachees a EFA + annee)
- Modulation dossier (rattache a PerimeterEvent)
- Multi-entite declaration (entre EFA et Organisation)
- Historique declaration (versioning)

**Cas geres :**
- 1 site = 1 batiment : OK (auto-creation Sprint 1)
- 1 site = N batiments : OK (TertiaireEfaBuilding)
- Multi-compteurs : OK
- Donnees manquantes : OK (DataQualityIssue)

**Cas NON geres :**
- Batiment mixte (multi-usage) : KO (usage_label = string)
- Compteurs partages entre sites : KO (FK site_id unique)
- Multi-SIREN sur meme EFA : KO (pas de modele coordination)

## 4.4 UX/UI

**Points forts :**
- Separation claire BACS / OPERAT (pages distinctes)
- BacsWizard 4 phases (eligibilite → inventaire → resultat → plan)
- Putile live avec zones couleur (vert/ambre/rouge)
- TertiaireDashboard avec signaux (assujetti_probable, a_verifier)
- Drawer "Pourquoi ?" explicatif
- Catalogue preuves avec couverture %
- Timeline reglementaire multi-framework
- Labels FR structures (complianceLabels.fr.js)

**Points faibles critiques :**
- **Pas de porte d'eligibilite claire** : l'utilisateur ne voit pas en 1 clic s'il est assujetti
- **Score BACS non explique** : 75/100 = bon ou mauvais ?
- **Echeances OPERAT invisibles** : pas de deadline visible dans le dashboard Tertiaire
- **"Simulation" non clarifiee** : l'export OPERAT dit "simulation" mais l'utilisateur peut croire avoir depose
- **Pas de glossaire** : TRI, GTB, EFA, Putile non definis dans l'app
- **Couverture preuves opaque** : "60%" de quoi exactement ?
- **Pas d'inspection dans Tertiaire** : BACS a un countdown, Tertiaire n'a rien

## 4.5 Architecture / code

**Points forts :**
- Separation front/back claire
- Regles BACS versionnees dans YAML (`regulations/bacs/v2.yaml`)
- Engine versionne (`engine_version` dans BacsAssessment)
- Labels centralisees (`complianceLabels.fr.js`)
- Soft-delete unifie
- Tests unitaires BACS (25+ tests)

**Points faibles :**
- Duplication regles entre `compliance_engine.py` (deprecated) et `compliance_rules.py`
- Constants hardcodees en fallback (290/70/7500) quand le YAML existe
- Pas de separation claire "regle metier" vs "regle UI" pour Tertiaire
- Tests Tertiaire/OPERAT insuffisants (pas de test trajectoire, normalisation)

## 4.6 Preuve / audit-trail

**FAIL MAJEUR.** L'infrastructure preuve est un POC :
- Evidence model basique (site_id, type, statut, file_url)
- TertiaireProofArtifact lie a la KB mais sans workflow validation
- **Aucun journal de changement** sur les preuves (qui a approuve quand ?)
- **Aucun export certifie** (pas de checksum, pas de signature)
- **Aucune politique retention** (5 ans obligatoire BACS)
- **Pas d'upload fichier** (file_url = reference externe)
- ActionEvent est le seul bon modele d'audit (WHO/WHEN/WHAT)

## 4.7 Cas simples vs cas complexes

| Cas | Simple | Complexe |
|-----|--------|----------|
| 1 site bureau 500 m2 | Hors perimetre DT, BACS possible si CVC > 70 kW — detecte correctement | - |
| 1 site bureau 2000 m2 | Assujetti DT → EFA creee, mais pas de conso reference → bloque | - |
| Multi-batiments meme site | OK (TertiaireEfaBuilding supporte N batiments) | Surface coherence verifiee |
| Multi-sites multi-SIREN | - | KO — pas de coordination multi-entites |
| Batiment mixte | - | KO — usage_label = string unique |
| Renouvellement CVC | Declenchement correct | Pas de workflow pour documenter le renouvellement |

---

# 5. TOP 10 DES CORRECTIONS

| # | Objectif | Pourquoi | Fichiers | Effort | Risque si non fait | Deps |
|---|----------|----------|----------|--------|-------------------|------|
| 1 | **Modele consommation par EFA** (reference_year, current_year, normalized) | Sans baseline, trajectoire impossible | `tertiaire.py`, nouveau modele | L | Client pense etre conforme sans pouvoir le prouver | - |
| 2 | **Validation trajectoire** (-40%/-50%/-60%) | Coeur de la promesse OPERAT | `tertiaire_service.py`, nouveau endpoint | M | Aucun warning si trajectoire KO | #1 |
| 3 | **Audit-trail preuves** (ProofEventLog) | Indefendable en cas d'audit ADEME | Nouveau modele + middleware | M | Preuves non tracees = preuve nulle | - |
| 4 | **Clarifier "simulation" vs "depot reel"** dans l'UI | Le client peut croire avoir depose | `ExportOperatModal.jsx`, `TertiaireEfaDetailPage.jsx` | S | **DANGEREUX** — faux sentiment conformite | - |
| 5 | **Classe A/B systeme GTB** | Exigence decret BACS fondamentale | `bacs_models.py`, `bacs_engine.py` | S | BACS "conforme" avec systeme non eligible | - |
| 6 | **Normalisation climatique** (HDD/CDD/facteur) | Comparaisons biaisees sans normalisation | Nouveau modele + service | L | Consommations non comparables | #1 |
| 7 | **Detection perte efficacite BACS** | Exigence decret monitoring continu | `bacs_engine.py`, nouveau modele perf | M | Fonction BACS fondamentale absente | - |
| 8 | **Export certifie** (checksum + manifest) | Preuve non recevable sans integrite | `operat_export_service.py` | M | Export contestable juridiquement | - |
| 9 | **Porte eligibilite explicite** dans l'UI | L'utilisateur ne sait pas s'il est assujetti | `BacsWizard.jsx`, `TertiaireDashboardPage.jsx` | M | Confusion utilisateur | - |
| 10 | **Workflow modulation OPERAT** | Evenements perimetre sans approbation | Nouveau modele + endpoints | M | Modulations non documentees | - |

---

# 6. PLAN D'EXECUTION

## Sprint 0 — Cadrage (1 semaine)

- Arbitrage produit : quelle promesse conformite PROMEOS fait-il reellement ?
- Decision : "simulation" ou "depot assiste" pour OPERAT
- Decision : BACS = pilotage ou conformite attestation
- Prioriser : trajectoire OPERAT vs BACS classe A/B vs audit-trail
- Mapper les exigences reglementaires restantes en user stories

## Sprint 1 — Conformite minimale reelle (2 semaines)

**Backlog :**
1. Modele `TertiaireEfaConsumption` (efa_id, year, kwh_total, kwh_elec, kwh_gaz, is_normalized, source)
2. Champs `reference_year` + `reference_year_consumption_kwh` sur TertiaireEfa
3. Endpoint `POST /efa/{id}/consumption/declare` (baseline + courant)
4. Validation trajectoire (`GET /efa/{id}/targets/validate?year=2025`)
5. Champ `system_class` (A/B/C/D) sur BacsCvcSystem + verification dans findings
6. Clarifier "simulation" dans l'UI (wording + banniere warning)

**Quick wins :** #5 (1 enum + 1 finding), #6 (wording)
**Critere de done :** Un EFA peut stocker sa conso reference, calculer sa trajectoire, et l'utilisateur voit clairement si c'est une simulation.

## Sprint 2 — Fiabilisation preuve et workflow (2 semaines)

**Backlog :**
1. Modele `ProofEventLog` (proof_id, user_id, action, old_status, new_status, timestamp)
2. Middleware logging sur Evidence, TertiaireProofArtifact, CeeDossierEvidence
3. Champs export (exported_at, exported_by, export_checksum) sur TertiaireDeclaration
4. Manifest export (liste preuves incluses + hash)
5. Workflow modulation (`TertiaireModulationDossier` : statut, facteur, approbation)
6. Detection perte efficacite BACS (baseline + seuil + alerte)

**Quick wins :** #3 (3 champs), #1 (1 modele)
**Critere de done :** Chaque changement de statut preuve est trace. Les exports ont un checksum. Les modulations ont un workflow.

## Sprint 3 — Excellence UX + industrialisation (2 semaines)

**Backlog :**
1. Porte eligibilite BACS (phase 0 wizard : "Etes-vous assujetti ?")
2. Explication score BACS (tooltip avec seuils 0-25/26-50/51-75/76-100)
3. Deadline visible dans Tertiaire dashboard
4. Glossaire in-app (TRI, GTB, EFA, Putile, OPERAT)
5. Normalisation climatique (modele HDD/CDD + facteur)
6. Zones fonctionnelles BACS (modele BacsZone)
7. Checklist pre-depot OPERAT dans l'UI

**Quick wins :** #2 (tooltip), #4 (glossaire modal)
**Critere de done :** L'utilisateur comprend s'il est assujetti, ce qui lui manque, et ce qu'il risque. La normalisation climatique est disponible.

---

# 7. ANNEXE

## Fichiers audites

### Backend
- `models/bacs_models.py` — BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection
- `models/tertiaire.py` — TertiaireEfa, EfaBuilding, Declaration, Responsibility, PerimeterEvent, ProofArtifact, DataQualityIssue
- `models/evidence.py` — Evidence, TypeEvidence, StatutEvidence
- `models/enums.py` — CvcSystemType, CvcArchitecture, BacsTriggerReason, InspectionStatus
- `services/bacs_engine.py` — compute_putile, determine_obligation, compute_tri, evaluate_bacs
- `services/tertiaire_service.py` — qualify_efa, run_controls, precheck_declaration, generate_operat_pack
- `services/operat_export_service.py` — validate_operat_export, generate_operat_csv
- `services/compliance_engine.py` — legacy compliance (deprecated)
- `services/compliance_rules.py` — _eval_bacs, _eval_decret_tertiaire
- `services/bacs_ops_monitor.py` — KPIs monitoring BACS
- `services/tertiaire_proofs.py` — catalogue preuves
- `services/tertiaire_proof_catalog.py` — mapping issues → preuves
- `routes/bacs.py` — endpoints BACS
- `routes/tertiaire.py` — endpoints Tertiaire/EFA
- `routes/operat.py` — export OPERAT
- `regulations/bacs/v2.yaml` — config reglementaire BACS
- `regops/config/regs.yaml` — config penalites
- `tests/test_bacs_engine.py` — 25+ tests BACS

### Frontend
- `pages/ConformitePage.jsx` — cockpit conformite 4 onglets
- `pages/tertiaire/TertiaireDashboardPage.jsx` — dashboard EFA
- `pages/tertiaire/TertiaireEfaDetailPage.jsx` — detail EFA
- `components/BacsWizard.jsx` — wizard BACS 4 phases
- `components/BacsOpsPanel.jsx` — monitoring BACS
- `components/ExportOperatModal.jsx` — export CSV
- `components/compliance/RegulatoryTimeline.jsx` — frise reglementaire
- `domain/compliance/complianceLabels.fr.js` — labels FR

## Zones non auditees
- Integration API OPERAT reelle (pas d'API OPERAT dans le repo)
- Integration EMS/pilotage × BACS
- Securite/permissions granulaires sur les preuves
- Performance requetes sur gros patrimoine (> 100 sites)

## Hypotheses
- H1 : PROMEOS vise "aide a la conformite" et non "outil de depot reglementaire" — sinon l'ecart est plus grave
- H2 : Le modele EFA est aligne sur la structure OPERAT officielle — non verifie contre le schema OPERAT reel
- H3 : Les seuils BACS sont a jour (pas de modification reglementaire post-2024)

## Dettes techniques detectees
- `compliance_engine.py` marque deprecated mais toujours utilise
- Constantes BACS dupliquees (YAML + hardcode fallback)
- Penalite BACS 7500 EUR hardcodee dans l'engine
- Score BACS trop simpliste (formule lineaire sans granularite)
- Tests OPERAT quasi-absents (pas de test trajectoire, normalisation, multi-entite)

## Points a arbitrer cote produit
1. PROMEOS promet-il la conformite ou l'aide a la conformite ? (impacte le wording et la responsabilite)
2. Le depot OPERAT doit-il etre reel (API ADEME) ou rester en simulation assistee ?
3. La normalisation climatique est-elle indispensable au MVP ou peut attendre ?
4. Les zones fonctionnelles BACS sont-elles requises pour les premiers clients ou reportables ?
5. Le multi-SIREN est-il dans le scope actuel ou futur ?
