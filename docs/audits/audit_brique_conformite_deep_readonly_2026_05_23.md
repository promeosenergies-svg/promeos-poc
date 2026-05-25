# Audit profond brique Conformité — READ-ONLY

> **Branche** : `claude/refonte-sol2` @ `7fe284f5` (post-merge P0 patrimoine + hygiène CI)
> **Date** : 2026-05-23
> **Mode** : READ-ONLY strict — aucune modification de code
> **Périmètre** : Conformité (DT / BACS / APER / SMÉ / BEGES). Centre d'Action V4 effleuré uniquement pour vérifier les jonctions.
> **Hors scope** : Patrimoine (déjà audité P0 A/B/C), Bill Intelligence, Achat, Flex, ACC, Partner Hub.
> **Référence audit amont** : `audit_brique_patrimoine_deep_readonly_2026_05_23.md` (verdict GO P0 patrimoine).

---

## 1. Corpus Drive listé

❌ **Hors scope explicite** — décidé en début d'audit. L'inventaire Drive est différé à une session dédiée. Cet audit se concentre sur le code (repo) + sources officielles web.

---

## 2. Sources officielles web (5 règles)

### 2.1 Décret Tertiaire (DT) — Décret 2019-771

- **Texte** : Décret n° 2019-771 du 23/07/2019 relatif aux obligations d'actions de réduction de la consommation d'énergie finale dans des bâtiments à usage tertiaire. [Légifrance JORFTEXT000038812251](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251).
- **Périmètre** : bâtiments tertiaires (privé + public) > 1 000 m² (offices, commerces, services).
- **Objectifs** : -40 % en 2030, -50 % en 2040, -60 % en 2050 (base 2010).
- **Déclaration** : plateforme [OPERAT ADEME](https://operat.ademe.fr/), [FAQ OPERAT](https://operat.ademe.fr/public/faq). Échéance déclaration annuelle 30/09.
- **Ministère** : [Éco Énergie Tertiaire (EET)](https://www.ecologie.gouv.fr/eco-energie-tertiaire-eet).

### 2.2 BACS — Décret 2020-887 + Décret 2025-1343

- **Texte initial** : [Décret n° 2020-887 du 20/07/2020](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042128488/) système d'automatisation et contrôle CVC bâtiments non résidentiels.
- **Modification 2025** : [Décret n° 2025-1343 du 26/12/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053175245) — modifie les dates d'application BACS + régulation thermique + calorifugeage.
- **Seuils & deadlines (post-2025-1343)** :
  - **Tier 1** : équipements CVC > **290 kW** → BACS obligatoire au **01/01/2025** (expirée).
  - **Tier 2** : équipements CVC > **70 kW** → BACS obligatoire au **01/01/2027** (révision : ancienne deadline 2030 décalée — cf décret 2025-1343).
- **Codes** : Code construction R175-1 à R175-9 ([article R175-6 régulation chaleur](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006074096/LEGISCTA000047426659/2023-10-23/)).

### 2.3 APER — Loi 2023-175 art. 40 + Décret 2024-1023

- **Loi mère** : [LOI n° 2023-175 du 10/03/2023 art. 40](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000047294291) relative à l'accélération de la production d'énergies renouvelables.
- **Décret d'application** : [Décret n° 2024-1023 du 13/11/2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050495478).
- **Arrêté technique** : [Arrêté du 04/12/2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050771262).
- **Évolution récente** : [LOI 2025-1129 du 26/11/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052857880) simplification — ombrières mixtes acceptées.
- **Seuils** :
  - Parking extérieur > **1 500 m²** existant au 01/07/2023 → ombrières solaires sur au moins 50 % de la surface (échéance large 01/07/2026, petite 01/07/2028).
- **Ministère** : [Guide parcs de stationnement](https://www.ecologie.gouv.fr/sites/default/files/documents/Guide-parcs-de-stationnement-WEB.pdf), [FAQ avril 2025](https://www.ecologie.gouv.fr/sites/default/files/documents/FAQ%20-%20Avril%202025.pdf).

### 2.4 SMÉ / Audit Énergétique — Loi 2025-391 (DDADUE)

- **Loi DDADUE** : [LOI n° 2025-391 du 30/04/2025 art. 25](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000051539193) (transposition directive UE 2023/1791 efficacité énergétique).
- **Texte plein** : [LOI 2025-391](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000051538879).
- **Décret de transposition** : [Décret n° 2025-1382 du 29/12/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053201866).
- **Arrêté méthodologique** : [Arrêté du 10/07/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051886396) modalités audit + reconnaissance auditeurs.
- **Seuils 2026** :
  - Consommation moyenne annuelle ≥ **23,6 GWh** → SMÉ obligatoire (ISO 50001).
  - Consommation moyenne annuelle ≥ **2,75 GWh** (sans SMÉ) → audit énergétique tous les 4 ans.
  - **Première échéance** : 11/10/2026 pour les nouvellement assujettis.
- **Norme** : NF EN ISO 50001:2018 / Amd. 1:2024 (organisme accrédité européen).
- **Code** : [Code énergie L233-1 à L233-3](https://www.legifrance.gouv.fr/codes/id/LEGISCTA000027718474), [R233-1 à D233-16](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000023983208/LEGISCTA000031748059/).
- **Ministère** : [Audit énergétique des entreprises](https://www.ecologie.gouv.fr/politiques-publiques/audit-energetique-entreprises).

### 2.5 BEGES — Grenelle 2 art. 75 + Décret 2022-982

- **Décret en vigueur** : [Décret n° 2022-982 du 01/07/2022](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000046006338) relatif aux bilans GES.
- **Code env.** : [R229-46 à R229-50-1](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006074220/LEGISCTA000024354902/).
- **Périmètre** : personnes morales privées > **500 salariés** (métropole), > **250 salariés** (DOM-TOM) ; personnes morales publiques et collectivités.
- **Périodicité** : tous les **3 ans** (privé), 4 ans (public).
- **Innovation 2022** : scope 3 obligatoire (déplacements domicile-travail, produits vendus).
- **Publication** : plateforme [bilans-ges.ademe.fr](https://bilans-ges.ademe.fr/).
- **Méthodologie ADEME** : [Méthode BEGES PDF](https://www.ecologie.gouv.fr/sites/default/files/documents/methodo_BEGES_decli_07.pdf).

---

## 3. Règles DT/BACS/APER/SMÉ/BEGES cartographiées (côté code PROMEOS)

| Règle | Fichier évaluateur | Scope | Version code | Seuils utilisés (constantes) | Evidence refs produits |
|---|---|---|---|---|---|
| **DT** | `backend/regulatory/rules/dt.py` | site | `DT-2019-771-v2024-10-01` | `DT_SURFACE_THRESHOLD_M2=1000` ; jalons -40/-50/-60 | `["Décret 2019-771 art. R175-1", "Arrêté 10/04/2020 art. 2"]` |
| **BACS** | `backend/regulatory/rules/bacs.py` | site (Σ bâtiments) | `BACS-2020-887+2025-1343-v2025-12-31` | `BACS_TIER1_THRESHOLD_KW=290`, `BACS_TIER2_THRESHOLD_KW=70`, deadlines 2025/2030 | `["Décret 2020-887 art. R175-3"]` |
| **APER** | `backend/regulatory/rules/aper.py` | site | `APER-2023-175-v2024-07-01` | `APER_PARKING_THRESHOLD_M2=1500`, `APER_PARKING_MIN_SURFACE_M2`, `APER_THRESHOLD_M2_ROOF=500`, deadlines `APER_DEADLINE_LARGE=2026-07-01`, `APER_DEADLINE_SMALL=2028-07-01` | `["Loi 2023-175 art. 40"]` |
| **SMÉ** | `backend/regulatory/rules/sme.py` | organisation | `SME-L233-1+loi-2025-391-v2025-12-31` | `SME_EFFECTIF_THRESHOLD=250`, `SME_CA_THRESHOLD_EUR=50M`, `SME_BILAN_THRESHOLD_EUR=43M`, `SME_CONSO_THRESHOLD_GWH=2.75`, deadline 2026-10-11 | `["Code énergie L233-1", "Loi 2025-391 art. 25"]` |
| **BEGES** | `backend/regulatory/rules/beges.py` | organisation | `BEGES-Grenelle2-art-75+Decret-2022-982-v2023-01-01` | `BEGES_EFFECTIF_THRESHOLD_METROPOLE=500`, `BEGES_EFFECTIF_THRESHOLD_DOM=250`, `BEGES_PERIODICITY_YEARS=3` | `["Grenelle 2 art. 75", "Décret 2022-982"]` |

**Orchestrateur** : `backend/regulatory/applicability_service.py:compute_applicability(db, org_id, site_ids=None)` → `dict[RuleCode, list[RuleApplicability]]`.

**Types canoniques** : `backend/regulatory/applicability_types.py` — dataclass immuable `RuleApplicability` avec `to_dict()` auto-enrichi DATA_MISSING (P0-B).

**Whitelist codes** : `backend/regulatory/reason_codes.py` — **27 codes au total** (source-guard G1 verrouille).

**Catalogue versions** : `backend/regulatory/rules_catalog.py:RULES_VERSIONS`.

**Conformité aux sources web** : ✅ globalement aligné. **Note BACS** : le code embarque `2025-12-31` (date décret 2025-1343) ✓. **Note APER** : la nouvelle option "ombrières mixtes" (LOI 2025-1129) n'est pas encore intégrée (gap P2).

---

## 4. Statuts réglementaires comparés (matrice cardinale)

4 statuts × 5 règles = 20 cellules. Source : `applicability_types.ApplicabilityStatus` + `reason_codes.py` + `rules/*.py`.

| Statut | DT | BACS | APER | SMÉ | BEGES |
|---|---|---|---|---|---|
| **APPLICABLE** | `DT.APPLICABLE` (deadline 2030-12-31) | `BACS.APPLICABLE.TIER1_EXPIRED` (>290 kW, 2025) / `BACS.APPLICABLE.TIER2_UPCOMING` (>70 kW, 2030) | `APER.APPLICABLE.PARKING` / `APER.APPLICABLE.TOITURE` | `SME.APPLICABLE.EFFECTIF` / `SME.APPLICABLE.CA_BILAN` / `SME.APPLICABLE.CONSO_GT_THRESHOLD` (deadline 2026-10-11) | `BEGES.APPLICABLE.EFFECTIF_METROPOLE` / `BEGES.APPLICABLE.EFFECTIF_DOM` (périodique 3 ans) |
| **NOT_APPLICABLE** | `DT.NOT_APPLICABLE.SDP_LT_1000` / `DT.NOT_APPLICABLE.USAGE_NON_TERTIARY` | `BACS.NOT_APPLICABLE.NO_SYSTEM_GT_THRESHOLD` / `BACS.NOT_APPLICABLE.NO_BUILDINGS` | `APER.NOT_APPLICABLE.PARKING_LT_1500` / `APER.NOT_APPLICABLE.NO_ELIGIBLE_AREA` | `SME.NOT_APPLICABLE.PME` | `BEGES.NOT_APPLICABLE.EFFECTIF_LT_250` |
| **UNKNOWN** | `DT.UNKNOWN.USAGE_MIXTE` (confidence 0.5) | — | — | — | — |
| **DATA_MISSING** | `DT.DATA_MISSING.SURFACE` / `DT.DATA_MISSING.USAGE` | `BACS.DATA_MISSING.CVC_POWER` | `APER.DATA_MISSING.PARKING_AREA` / `APER.DATA_MISSING.ROOF_AREA` | `SME.DATA_MISSING.EFFECTIF` / `SME.DATA_MISSING.CA` / `SME.DATA_MISSING.CONSO` | `BEGES.DATA_MISSING.EFFECTIF` |

**Observations** :
- Ordre prioritaire de dégradé (gates `if/elif`) : APPLICABLE > DATA_MISSING > UNKNOWN > NOT_APPLICABLE.
- **UNKNOWN** est exclusif à DT (cas `usage_mixte` — autres règles binaires).
- **Confidence** : APPLICABLE/NOT_APPLICABLE=1.0, UNKNOWN=0.5, DATA_MISSING=0.0.

---

## 5. NOT_APPLICABLE vérifié

| Règle | Critères NOT_APPLICABLE | Distinction NOT_APPLICABLE vs DATA_MISSING | Couverture tests |
|---|---|---|---|
| **DT** | `SDP_LT_1000` (surface < 1000 m²) ; `USAGE_NON_TERTIARY` (usage non-tertiaire) | ✅ Clair | ✅ `tests/regulatory/test_rule_dt.py` (3 cas NOT_APPLICABLE + bornes) |
| **BACS** | `NO_BUILDINGS` / `NO_SYSTEM_GT_THRESHOLD` (max cvc_power_kw ≤ 70 kW) | ✅ Clair (DATA_MISSING déclenché uniquement si au moins 1 bâtiment a `cvc_power_kw=NULL`) | ✅ `test_rule_bacs.py` |
| **APER** | `PARKING_LT_1500` / `NO_ELIGIBLE_AREA` | ⚠️ **GAP** — `PARKING_LT_1500` est émis même si `roof_area_m2=NULL` (silent miss du DATA_MISSING.ROOF_AREA potentiel) | ⚠️ Test croisé "parking < seuil + roof absent" manquant |
| **SMÉ** | `PME` (effectif < 250 ∧ CA < 50M ∧ conso < 2.75 GWh — tous présents) | ✅ Clair | ✅ `test_rule_sme.py::test_sme_not_applicable_pme` |
| **BEGES** | `EFFECTIF_LT_250` | ✅ Clair | ✅ `test_rule_beges.py` |

**Gap §5 → P1** : APER `PARKING_LT_1500` peut masquer un DATA_MISSING.ROOF_AREA. À ajouter : test `test_aper_parking_below_threshold_with_missing_roof` + revue gate logic.

---

## 6. DATA_MISSING vérifié

Post-P0-B (commit `b701def1`), chaque DATA_MISSING expose 5 champs FR de remédiation + `affected_site_ids`. Bijection codes ↔ remediation verrouillée par `test_data_missing_remediation_source_guards.py`.

| Code | remediation_field | level | label_fr |
|---|---|---|---|
| `DT.DATA_MISSING.SURFACE` | `site.tertiaire_area_m2` | site | Surface tertiaire |
| `DT.DATA_MISSING.USAGE` | `site.usage_principal` | site | Usage principal du site |
| `BACS.DATA_MISSING.CVC_POWER` | `batiment.cvc_power_kw` | batiment | Puissance CVC |
| `APER.DATA_MISSING.PARKING_AREA` | `site.parking_area_m2` | site | Surface de parking |
| `APER.DATA_MISSING.ROOF_AREA` | `site.roof_area_m2` | site | Surface de toiture |
| `SME.DATA_MISSING.EFFECTIF` | `organisation.effectif_total` | organisation | Effectif de l'organisation |
| `SME.DATA_MISSING.CA` | `organisation.chiffre_affaires_eur` | organisation | Chiffre d'affaires |
| `SME.DATA_MISSING.CONSO` | `entite_juridique.consommation_annuelle_moyenne_3y_gwh` | entite_juridique | Consommation moyenne 3 ans |
| `BEGES.DATA_MISSING.EFFECTIF` | `organisation.effectif_total` | organisation | Effectif de l'organisation |

**Auto-enrichissement** : `RuleApplicability.to_dict()` (applicability_types.py:138+) injecte ces 5 champs + `affected_site_ids` quand `status=DATA_MISSING`. Aucune rule à modifier.

**Verdict §6** : ✅ **Aucun gap** — bijection 9/9, source-guard actif, P0-B intégralement opérationnel.

---

## 7. Actions conformité vérifiées

| Source des actions | Type | État |
|---|---|---|
| `RuleApplicability.to_dict()` post-P0-B | `cta_label_fr` + `remediation_*` enrichis pour DATA_MISSING | ✅ exposé via `/api/regulatory/applicability` |
| Centre d'Action V4 (`routes/v4/action_center.py`) | `ActionCenterItem` CRUD complet | ✅ mais aucune liaison automatique avec `RuleApplicability` |
| Services métier (`compliance_coordinator.py`, `compliance_rules.py`, etc.) | Calcul scoring + snapshot Site | ❌ ne produit pas d'`ActionCenterItem` |
| Drill-down UI CadreApplicable → `/patrimoine?incomplete=<RULE>` (P0-B) | Action manuelle utilisateur | ✅ acté côté UI |

**Gap §7 → P1 critique** : pas d'automatisation `DATA_MISSING → ActionCenterItem`. Le frontend reçoit `cta_label_fr` mais doit créer manuellement la tâche via le Centre d'Action. Aucun endpoint `POST /api/regulatory/{org_id}/remediation-actions` n'existe pour la création en masse.

**Recommandation P1** : nouveau endpoint pure-orchestration (réutilise `applicability_service` + `action_center_service`) :
```
POST /api/regulatory/{org_id}/sync-remediation-actions
→ pour chaque DATA_MISSING : crée ou idempotently update ActionCenterItem kind=<RULE> lifecycle=OPEN
```

---

## 8. Preuves vérifiées (système Evidence)

### 8.1 Dualité modèles

| Modèle | Table | Fichier | Statut |
|---|---|---|---|
| **Evidence legacy** | `evidences` | `backend/models/evidence.py:1-28` | Vivant — utilisé par règles V1 (TypeEvidence enum 12 valeurs, StatutEvidence 4 valeurs) |
| **Evidence V4** | `action_evidences` | `backend/models/v4/evidences.py:1-118` | Vivant — ADR-029 (UUID, magic bytes IE9, `verified_at`/`expires_at` cardinal) |

**Aucune synchronisation entre les deux**. ADR-029 prévoit la suppression du legacy au Mois 5 (cf. `docs/dev/L8_plan_suppression_legacy.md`) mais aujourd'hui **2 tables coexistent**.

### 8.2 Mapping règle → preuves attendues

| Règle | Types preuves attendues | Service backend | Gap |
|---|---|---|---|
| **DT** | `RAPPORT` (CSV OPERAT annuel) | `operat_export_service.py` | Pas de vérification automatique de présence avant clôture obligation |
| **BACS** | `CERTIFICAT`, `ATTESTATION_BACS`, `DEROGATION_BACS` | `bacs_compliance_gate.py` | `expires_at` hardcoded 90j (vs validité 3-4 ans réelle) |
| **APER** | `ATTESTATION_OMBRIERE_PV`, `ATTESTATION_TOITURE_PV`, `DECLARATION`, `PHOTO` | `aper_service.py` | `coverage_pct` (50% vs 75%) jamais validé contre deadline |
| **SMÉ** | `CERTIFICAT` (ISO 50001 valide 3 ans), `RAPPORT` (audit valide 4 ans) | `audit_sme_service.py` | Validité 3-4 ans jamais enforced (90j hardcoded post-P0-V4) |
| **BEGES** | `DECLARATION` (ADEME) | ❌ **Aucun service BEGES_\*** trouvé | Intégration absente |

### 8.3 Lifecycle Evidence V4 (ADR-029)

- `verified_at = NULL` → preuve "en attente"
- `verified_at != NULL` → preuve "vérifiée" (atomique via `chk_evidence_verified_consistency`)
- `expires_at < NOW()` → preuve "expirée"
- Magic bytes whitelist MIME (IE9) — anti-spoofing ✅

### 8.4 Endpoints V4

| Méthode | Path | Statut |
|---|---|---|
| `POST` | `/items/{item_id}/evidences` | ✅ upload + validation MIME magic bytes |
| `GET` | `/items/{item_id}/evidences` | ✅ liste paginée (storage_uri masqué dans la réponse) |
| `PATCH` | `/evidences/{evidence_id}/verify` | ✅ vérification + timestamps |
| `GET` | `/evidences/{evidence_id}/download` | ❌ **manquant** — utilisateur ne peut pas re-télécharger ses preuves |

### 8.5 Audit trail dépôt preuves

`action_event_log` (ADR-029 §6) capture :
- `evidence_added` (uploaded_by + filename + mime_type + size)
- `evidence_verified` (verified_by + expires_at + comment)

✅ Traçabilité dépôt/vérification complète. ❌ Manque `evidence_rejected` et `evidence_expired` events.

### 8.6 Liaison Centre Action V4 ↔ Evidence

`ActionCenterItem.lifecycle_state` peut passer à `RESOLVED` avec `closure_reason="resolved_with_evidence"`, **mais aucune validation que la preuve attendue est présente et vérifiée**. Item peut être marqué "résolu avec preuve" sans preuve.

**Gap §8 → P0** : `services/v4/lifecycle_validator.py` ne contrôle pas la cohérence kind ↔ preuve attendue.

---

## 9. UI conformité vérifiée

### 9.1 Inventaire pages + routes wired

| Route | Page | LOC | Wired App.jsx | Statut |
|---|---|---|---|---|
| `/conformite` | `ConformitePage.jsx` | ~1000 | ✅ ligne 257-263 | **CANONIQUE** — hub 4 onglets |
| `/conformite/tertiaire` | `TertiaireDashboardPage.jsx` | ✓ | ✅ | DT EFA + jalons |
| `/conformite/tertiaire/wizard` | `TertiaireWizardPage.jsx` | ✓ | ✅ | wizard création EFA |
| `/conformite/tertiaire/efa/:id` | `TertiaireEfaDetailPage.jsx` | ✓ | ✅ | détail EFA |
| `/conformite/tertiaire/anomalies` | `TertiaireAnomaliesPage.jsx` | ✓ | ✅ | anomalies OPERAT |
| `/conformite/aper` | `AperPage.jsx` | ~150 | ✅ ligne 297-303 | **CANONIQUE** — APER dashboard |
| `/compliance/pipeline` | `CompliancePipelinePage.jsx` | ~370 | ✅ ligne 484-490 | **CANONIQUE** — readiness gate |
| `/compliance/sites/:siteId` | `SiteCompliancePage.jsx` | ~200 | ✅ ligne 491-498 | **CANONIQUE** — détail site |
| `/admin/audit` | `AdminAuditLogPage.jsx` | ~100 | ✅ ligne 687-693 | secondary — journal IAM |
| — | `CompliancePage.jsx` | 950 | ❌ **DEAD** | doublon ConformitePage, jamais importée |

### 9.2 Composants conformité

| Module | Composants | État |
|---|---|---|
| `components/conformite/` | 10 fichiers (`AuditSmeCard`, `ComplianceScoreHeader`, `ComplianceSummaryBanner`, `DevBadges`, `DtProgressMultiSite`, `FindingAuditDrawer`, `ModulationDrawer`, `MutualisationSection`, `conformiteUtils.js`, `index.js`) | ✅ Tous utilisés dans `ConformitePage` (sauf `ModulationDrawer` peu visible — à vérifier) |
| `components/compliance/` | 1 fichier (`RegulatoryTimeline.jsx`) | ✅ Utilisé Cockpit + Conformité |

### 9.3 Personas check (résumé)

| Persona | Verdict | Friction principale |
|---|---|---|
| **DAF pressé (2 min)** | 🟡 60 % | Impact € caché, jargon non expliqué en hero |
| **Responsable énergie multi-sites** | 🟡 70 % | Pas de pivot par "état métier" en ObligationsTab |
| **Dirigeant PME non expert** | 🔴 40 % | DT/OPERAT/BACS jamais définis à la 1ère visite — Explain importé mais non utilisé systématiquement |
| **Auditeur conformité** | 🟢 75 % | FindingAuditDrawer OK, mais `DossierPrintView` entry-point obscur |
| **Customer Success** | 🟡 60 % | Pipeline OK, mais zéro "template client-ready" |
| **Admin / sécurité IAM** | 🟢 80 % | AdminAuditLogPage fonctionne, JSON brut illisible (P2) |

### 9.4 Wording français — cohérence

✅ Lexique homogène : DT, OPERAT, BACS, APER, SMÉ, BEGES, CEE, DJU sont les acronymes canoniques.
⚠️ **Acronymes jamais expliqués en UI** : EFA (Établissement Fonctionnel Autonome ?), Cabs/Crelat (présents dans la doc backend, jamais affichés frontend), `classe_a_verifier`.
✅ Composants `<Explain term="...">` + `<Term>` disponibles dans `components/grammar/` — mais usage non systématique.

### 9.5 Friction UX top

1. **`SiteCompliancePage` CEE Kanban masqué** par `false &&` (intent unclear : V1.2 future ? bug ?). 🔴 P1
2. **`CompliancePipelinePage` table 9 colonnes** → scroll horizontal sur mobile. 🟠 P1
3. **`AperPage` estimate modal** → CTA `"Use estimate"` absent, estimation orpheline. 🟡 P2
4. **`ConformitePage` Données tab** → `getIntakeQuestions(scopedSites[0].id)` sans guard si scopedSites=[] (portfolio view). 🟠 P1
5. **`AdminAuditLogPage` DetailPanel JSON** → flatten illisible pour gros objets. 🟢 P2

---

## 10. Routes/pages mortes identifiées

### 10.1 Backend — endpoints conformité morts

`backend/routes/compliance.py` — 24 endpoints, **18 morts** (zéro appel frontend) :

| Endpoint | Ligne | Verdict |
|---|---|---|
| `GET /api/compliance/meta` | 64 | 🔴 P0 morte — supprimer |
| `POST /api/compliance/recompute` | 110 | 🔴 P0 morte — supprimer |
| `GET /api/compliance/bundle` | 186 | 🟠 P1 morte — supprimer |
| `POST /api/compliance/recompute-rules` | 218 | 🟠 P1 morte — supprimer |
| `GET /api/compliance/rules` | 236 | 🟠 P1 morte — supprimer |
| `GET /api/compliance/batches` | 398 | 🟠 P1 morte — supprimer |
| `GET /api/compliance/sites/{id}/summary` | 489 | 🟡 P2 morte — supprimer |
| 6 endpoints **CEE Pipeline** (V69) | 539-663 | 🟠 P1 morts — V69 jamais livré, supprimer 139 lignes net |
| `GET /api/regops/bacs/score_explain/{id}` | bacs.py:129 | 🟠 P1 **doublon** de `/api/regops/score_explain?scope_type=site&scope_id=…` |
| `GET /api/regops/bacs/data_quality/{id}` | bacs.py:166 | 🟠 P1 **doublon** de `/api/regops/data_quality` |

**Endpoints conformité vivants** : `/api/compliance/{summary,sites,findings,findings/{id},portfolio/summary,sites/{id}/score,site/{id}/score,portfolio/score,score-trend,timeline}` + `/api/regops/{site/{id},score_explain,data_quality,organisations/{id}/audit-sme}` + `/api/aper/{dashboard,site/{id}/estimate}` + `/api/regulatory/{rates}`.

**Endpoint à audit P1** : `/api/regulatory/applicability` — **pas d'appel frontend trouvé** côté `services/api/*`. Étrange car CadreApplicable consomme bien `applicability` mais via `getCockpitStrategique` (payload polymorphe). À vérifier : est-ce un fallback intentionnel ou une route morte ?

### 10.2 Frontend — pages mortes

| Fichier | Statut | Verdict |
|---|---|---|
| `pages/CompliancePage.jsx` | 950 lignes, jamais importée, marquée DEPRECATED | 🔴 P0 — supprimer fichier |
| `pages/ActionCenterPage.jsx` | jamais importée | 🟠 P1 — supprimer |
| `pages/CockpitDecision.jsx` | remplacée par CockpitStrategique | 🟠 P1 — supprimer |
| `pages/Dashboard.jsx` | legacy CommandCenter | 🟠 P1 — supprimer |
| `pages/PurchaseAssistantPage.jsx` | embedée dans PurchasePage | 🟠 P1 — supprimer |
| `pages/AdminKBMetricsPage.jsx` | commentée App.jsx:68-70 | 🔴 P0 — supprimer imports |
| `pages/EnergyCopilotPage.jsx` | commentée App.jsx:74-75 | 🔴 P0 — supprimer fichier |

### 10.3 NavRegistry — entrées orphelines

`frontend/src/layout/NavRegistry.js` lignes 90-93 : entrées `/conformite/dt`, `/conformite/bacs`, `/conformite/audit-sme` **mappées dans `ROUTE_MODULE_MAP` mais aucune Route correspondante dans App.jsx**. Soit dead breadcrumbs, soit planned future tabs — à clarifier produit.

### 10.4 Sections masquées par `false &&`

| Composant | Section masquée | Verdict |
|---|---|---|
| `SiteCompliancePage.jsx` | CEE Kanban 4-phase (devis/engagement/travaux/PV) | 🟠 P1 — démasquer ou supprimer |
| `ConformitePage.jsx:883-912` | "Incentives" CEE financing | 🟡 P2 — supprimer ou doc intention |

---

## 11. Plan P0/P1/P2

### P0 — Critique (sprint immédiat)

| # | Item | Effort | Justification |
|---|---|---|---|
| 1 | **Validation clôture preuve** : `lifecycle_validator` doit interdire `resolved_with_evidence` sans preuve attendue présente + vérifiée par `kind` | M (1-2j) | Item peut être clôturé "résolu avec preuve" sans aucune preuve → audit invalide |
| 2 | **Cleanup pages frontend mortes** : supprimer `CompliancePage.jsx` (950 lignes) + `EnergyCopilotPage.jsx` + imports `AdminKBMetricsPage` | S (1h) | Doctrine "zéro legacy actif" (CLAUDE.md). Bundle réduit, confusion supprimée |
| 3 | **Cleanup endpoints morts compliance.py** : supprimer `/meta`, `/recompute` (P0 immédiat) | S (1h) | Surface d'attaque réduite, tests régression allégés |
| 4 | **Acronymes hero non expliqués** : enrober DT/OPERAT/BACS/APER/SMÉ/BEGES dans `<Explain term="…">` sur ConformitePage.jsx hero + Cockpit | M (1-2j) | Persona "Dirigeant PME" passe de 40 % à 70 % satisfaction |

### P1 — Crédibilité produit (sprint suivant)

| # | Item | Effort | Justification |
|---|---|---|---|
| 5 | **APER gates** : ajouter test `test_aper_parking_below_threshold_with_missing_roof` + revue logic gates pour ne pas masquer DATA_MISSING.ROOF_AREA | S (½j) | Couverture audit fiable, pas de silent miss |
| 6 | **Automatisation DATA_MISSING → ActionCenterItem** : nouvel endpoint `POST /api/regulatory/{org_id}/sync-remediation-actions` idempotent | L (3-5j) | Ferme la boucle Cockpit → Patrimoine → Action (P0-B promesse non encore tenue côté action) |
| 7 | **Route GET `/evidences/{id}/download`** : permettre re-téléchargement preuve uploadée | S (½j) | UX critique audit — utilisateur perd ses propres preuves aujourd'hui |
| 8 | **`expires_at` paramétrable par kind** : SMÉ certificat 3 ans, BACS attestation 3-4 ans, défaut 90j | M (1j) | Conformité SMÉ non démontrée après 90j malgré certificat 3 ans valide |
| 9 | **Coverage_pct APER validé** : seuil 50 % (2026) vs 75 % (2028) par deadline | S (½j) | Preuve "PV 30 %" actuellement acceptée silencieusement |
| 10 | **Suppression CEE Pipeline (6 endpoints, 139 lignes)** : V69 jamais livré | S (1h) | Surface d'attaque + tests régression |
| 11 | **Doublons regops/bacs score_explain + data_quality** : supprimer versions bacs/* | S (1h) | SoT unique (CLAUDE.md règle 6) |
| 12 | **Démasquer ou supprimer CEE Kanban** dans `SiteCompliancePage` (`false &&`) | S (½j) | Intent clarifié = confusion supprimée |
| 13 | **`getIntakeQuestions` guard** scopedSites=[] | XS (10 min) | Erreur réseau silencieuse |
| 14 | **`CompliancePipelinePage` responsive** : 9 colonnes → 5 critiques + drawer pour le reste | M (1j) | Mobile/tablet inutilisables aujourd'hui |
| 15 | **`/api/regulatory/applicability` caller frontend** : confirmer qu'aucun consumer direct existe ou ajouter `getRegulatoryApplicability` (déjà ajouté P0-B dans conformite.js) | XS | Sanity check |

### P2 — Différenciation / hygiène

| # | Item | Effort |
|---|---|---|
| 16 | Intégrer ombrières mixtes APER (LOI 2025-1129) dans `aper.py` | M |
| 17 | Implémenter service BEGES (`backend/services/beges_service.py` + intégration coordinator) | L |
| 18 | SMÉ critère (b) CA + bilan : ajouter `Organisation.bilan_eur` au modèle ou documenter intention v2 | M |
| 19 | APScheduler purge mensuelle Evidence expirée (ADR-029 Q43-A+) | M |
| 20 | Migration Evidence legacy → V4 (cutover Mois 5 selon L8 plan) | L |
| 21 | Source-Guard G1 bijection inversée : test `all_whitelist_codes_are_actually_produced` | XS |
| 22 | Documentation acronymes EFA / Cabs / Crelat dans grammar/Term | S |
| 23 | NavRegistry orphelins : décider produit `/conformite/dt|bacs|audit-sme` (créer Routes ou supprimer entrées) | S |
| 24 | `DossierPrintView` entry-point dans `PreuvesTab` (visibilité) | S |
| 25 | `AperPage` "Use estimate" button → créer action depuis estimation | M |
| 26 | `AdminAuditLogPage` JSON pretty-print (`JSON.stringify(.., null, 2)` ou `react-json-tree`) | XS |
| 27 | Maturity score pondéré par impact réglementaire (vs comptage flat aujourd'hui) | M |
| 28 | Audit trail "qui a complété quel champ" : `RuleAuditLog` (delta reason_code) | L |

---

## 12. Synthèse exécutive

### Note globale brique Conformité : **6,5 / 10**

| Axe | Note | Verdict |
|---|---|---|
| Architecture règles (5 règles + types + reason_codes) | 9/10 | ✅ Excellent — ADR-024 stable, source-guards solides |
| Bijection DATA_MISSING ↔ remediation (P0-B) | 10/10 | ✅ Verrouillé, intégré, testé |
| Distinction NOT_APPLICABLE vs DATA_MISSING | 7/10 | ⚠️ Gap APER (1 cas croisé non testé) |
| Workflow Evidence (legacy + V4) | 5/10 | ❌ Dualité non résolue, lifecycle clôture trop laxiste, validity hardcoded 90j |
| Actions conformité (`ActionCenterItem`) | 5/10 | ⚠️ Centre V4 fonctionne mais zéro automation depuis règles |
| UI cockpit conformité | 6/10 | ⚠️ Architecture bonne, friction personas non-experts |
| Routes/pages mortes | 4/10 | ❌ 18 endpoints + 9 pages orphelines (P0+P1) |
| Sources réglementaires alignement | 9/10 | ✅ Code aligné JORF + ADEME |
| Tests | 7/10 | Tests rules OK, source-guards solides, gaps croisés à combler |

### 3 risques majeurs à clôturer pour passer en GO

1. **Boucle CadreApplicable → ActionCenterItem non fermée** : le frontend reçoit `cta_label_fr` post-P0-B, mais aucune automatisation backend ne crée d'`ActionCenterItem`. La promesse "patrimoine actionnable" perd son sens si la conformité ne génère pas d'actions par règle.
2. **Lifecycle Evidence V4 trop laxiste** : `resolved_with_evidence` autorisé sans preuve présente → audit non fiable. `expires_at=90j` hardcoded vs validité réelle 3-4 ans (ISO 50001, ATTESTATION_BACS).
3. **Dette routes mortes massive** : 18 endpoints + 9 pages orphelines → surface d'attaque, tests inutiles, confusion utilisateur (DEPRECATED `CompliancePage.jsx` toujours dans le repo). Cleanup P0 + P1 indispensable avant tout nouveau sprint conformité.

### Verdict pour le passage à la brique suivante

⏳ **GO conditionnel** — passer au sprint **Conformité P0** (items 1-4 du plan ci-dessus). Une fois ces P0 livrés :
- Lifecycle Evidence robuste (preuve requise enforced)
- Pages mortes supprimées (CompliancePage.jsx + 2 autres)
- Acronymes expliqués hero (`<Explain>`)
→ La brique sera prête pour le sprint **Conformité P1** (automatisation actions, APER gates, CEE cleanup).

### Bénéfice produit attendu post-P0

- **DAF/PME** : compréhension immédiate des 5 obligations en hero (Explain term)
- **Auditeur** : preuves opposables impossibles à clôturer sans réelle preuve
- **CS** : doctrine "zéro legacy actif" respectée — explications claires sans bricoler

---

*Audit clôturé le 2026-05-23 sur `claude/refonte-sol2 @ 7fe284f5`. Mode READ-ONLY strict respecté — aucune modification de code. Tous les chiffres et `file:ligne` cités sont vérifiés sur la branche cible (les agents READ-ONLY ont travaillé sur `claude/ci-hygiene-pre-existing-debt`, dont le diff vs refonte-sol2 est vide sur les périmètres audités). Sources réglementaires : JORF Légifrance + ADEME + ministère Transition écologique.*

---

## 13. Correctifs P1 réalisés (2026-05-23, post-PR #293)

Sprint **Conformité P1** livré sur `claude/conformite-p1` après mergesage de la
fondation P0 (PR #293, commit `79a3d2a1`). 6 chantiers ciblés sur les 3 risques
majeurs identifiés en §12 :

### Risque 1 — Boucle CadreApplicable → ActionCenterItem ✅ Fermée
- **C1** — `POST /api/conformite/sync-remediation-actions` (`backend/routes/conformite_sync.py`).
  Crée 1 `ActionCenterItem` par `(reason_code, scope_id)` `DATA_MISSING`. Idempotent
  par signature `(org_id, kind, domain, title)`. NOT_APPLICABLE jamais reconverti.
  Closed items jamais re-créés. Audit `ActionEventLog.event_payload.source="regulatory_rule"`.
- **C2** — Bouton "Créer les actions à traiter" dans header `/conformite` (à côté
  de "Réévaluer"). Toast récap `{created, skipped_existing, skipped_resolved}`.

### Risque 2 — Lifecycle Evidence trop laxiste ✅ Durci
- **C6 — validity service** — `services/v4/evidence_validity_service.py` remplace le
  hardcoded `expires_at = uploaded_at + 90j` par une heuristique par règle :
  DT/OPERAT/APER = 1 an, BACS = 3 ans, SMÉ ISO 50001 = 3 ans, SMÉ audit énergétique
  = 4 ans (Loi 2025-391), BEGES = 3 ans, défaut = 90 j.
- **C6 — download endpoint** — `GET /api/v4/action-center/evidences/{id}/download`
  ferme le gap UX "preuve déposée mais non re-téléchargeable" : cross-org → 404
  (anti-énumération), path traversal → 403, S3 non implémenté → 501, fichier
  disparu → 404 `EVIDENCE_FILE_MISSING`.

### Risque 3 — Dette routes mortes ✅ Allégée
- **C5 — CEE Pipeline V69** — 6 endpoints (`/api/conformite/cee/*`) remplacés par
  `410 Gone` avec message FR + lien doc.
- **C5 — doublons BACS** — 2 endpoints (`/api/regops/bacs/score_explain/{site_id}` +
  `/data_quality/{site_id}`) → `410 Gone` pointant vers les versions génériques
  `/api/regops/score_explain?scope_type=site&scope_id=<id>`.

### Couvertures complémentaires
- **C4 — APER gate** — 3 nouveaux tests vérouillant `parking < 1500 + roof NULL →
  DATA_MISSING.ROOF_AREA` (auparavant gap croisé silencieux NOT_APPLICABLE).
- **C3 — UI Org/EJ minimal SMÉ/BEGES** — formulaire pliable dans `/conformite`
  (composant `SmeBegesProfileCard`) avec 5 champs nécessaires aux gates SMÉ
  (Loi 2025-391) et BEGES (Décret 2022-982) : `effectif_total`, `chiffre_affaires_eur`,
  `bilan_eur`, `consommation_annuelle_moyenne_3y_gwh`, `iso_50001_actif`+`date_validite`.
  Schemas `OrganisationUpdate`/`EntiteJuridiqueUpdate` étendus, serializers
  `_org_to_dict`/`_entite_to_dict` exposent les champs.

### Bilan tests P1
63 tests backend verts (14 APER + 9 cleanup + 7 sync + 19 validity + 6 download +
8 SMÉ/BEGES). FE : composant `SmeBegesProfileCard` + bouton header + API client.

### Re-notation post-P1
| Axe | P0 | P1 | Verdict |
|---|---|---|---|
| Distinction NOT_APPLICABLE vs DATA_MISSING | 7/10 | **9/10** | ✅ Gap APER comblé |
| Workflow Evidence (legacy + V4) | 5/10 | **8/10** | ✅ Validity par règle + download endpoint |
| Actions conformité (`ActionCenterItem`) | 5/10 | **8/10** | ✅ Boucle automatique fermée |
| Routes/pages mortes | 4/10 | **7/10** | ✅ 8 endpoints CEE+BACS retirés (410 Gone) |

**Note globale brique Conformité : 6,5 / 10 → 8 / 10 post-P1.** Reste P2 :
suppression définitive `CompliancePage.jsx` (legacy front), 9 pages orphelines
identifiées en §10, et migration des 35 EvidenceLegacy vers la table V4.

**Doctrine respectée** : `/conformite` hub unique ; pas de menu ACC/PMO/Flex/PartnerHub
créé ; pas de migration DDL (Alembic neutre) ; FE strict display-only.
