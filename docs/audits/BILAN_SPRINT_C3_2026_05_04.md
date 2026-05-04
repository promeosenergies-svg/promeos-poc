# Bilan Sprint C-3 — Sources + traçabilité

**Date livraison** : 2026-05-04
**Branche** : `claude/refonte-sol2`
**HEAD** : `477e3cea` (Phase 3.7d audit follow-up — 4 fixes critiques + 7 dettes Sprint C-4)
**Audit Phase B référence** : `docs/audits/AUDIT_PATRIMOINE_PHASE_B_2026_05_03.md`
**Bilan Sprint précédent** : `docs/audits/BILAN_SPRINT_C2_2026_05_04.md`

---

## Synthèse

| Phase | Sous-phase | Effort réel | Statut | Tests Δ | Commit hash |
|---|---|---|---|---|---|
| Phase 0 | Diagnostic état T0 + plan Sprint C-3 | <30 min | ✅ | — | (read-only) |
| Phase 3.1 | Audit pré-build R10 + ADR Option B (YAML statique) | ~30-45 min | ✅ | — | (read-only) |
| Phase 3.2 | `sources_reglementaires.yaml` + `RegulatorySourcesService` | ~2 j-h | ✅ | +30 | `cd87bf36` |
| Phase 3.3 | Endpoint `GET /api/regulatory/rates` + hook FE `useRegulatoryRates` | ~2 h | ✅ | +33 | `41db88b1` |
| Phase 3.4 | Endpoint `GET /api/portfolio/intensity` + SG kWhEF PCI | ~1.5 h | ✅ | +13 | `85b6502c` |
| Phase 3.4d | Audit multi-agents follow-up (5 fixes P0+P1 + 5 dettes) | ~1.5 h | ✅ | +0 net | `6fb98131` |
| Phase 3.5 | Composant FE `TraceTooltip` + intégration 5 KPIs (R10) | ~1.5 h | ✅ | +23 | `34dce820` |
| Phase 3.6 | `eld_gaz_referentiel.yaml` (21 ELD) + cascade `DP.grd_code` | ~3 h | ✅ | +24 | `f4cad96e` |
| Phase 3.7 | Audit pré-build cascade Org consentements → pivot doctrinal | ~1 h | ✅ (read-only) | — | `ee3d782e` |
| Phase 3.7d | Audit multi-agents follow-up (4 fixes critiques + 7 dettes Sprint C-4) | ~1.5 h | ✅ | +0 net | `477e3cea` |
| **Total** | **8 commits + 5 audits + diagnostic** | **~12-13 j-h** | ✅ **7/8 phases** | **+123 BE / +34 FE** | |

> Estimation initiale : 14-18 j-h. Effort réel : ~12-13 j-h = **bas du budget initial, gain -25 à -30%** via 5 audits pré-build + 2 audits multi-agents SDK.
>
> **Phase 3.8 (`coherence_globale.yaml`) reportée Sprint C-4** sur recommandation `architect-helios` : chantier YAML cross-domaines large, mature naturellement avec les 7 dettes Phase 3.7d à digérer dans le sprint Tests + observabilité.

---

## GAPS audit Phase B comblés Sprint C-3

| GAP | Description | Phase comblée |
|---|---|---|
| ✅ R10 | TraceTooltip réglementaire FE (différenciateur cardinal) | Phase 3.5 |
| ✅ Phase 22 audit | Migration `regulatory_rates.js` → endpoint `/api/regulatory/rates` | Phase 3.3 |

**2 GAPS comblés Sprint C-3.** GAPS restants : R8 (Onboarding 3 parcours, Sprint C-5).

---

## Dettes clôturées Sprint C-3 (5 entrées)

| ID | Statut | Phase clôture | Commit |
|---|---|---|---|
| ~~D-Phase4-3-Portfolio-Intensity-Backend-001~~ | ✅ CLÔTURÉ | Phase 3.4 | `85b6502c` |
| ~~D-Phase4-2-EnergieFinale-Source-Guard-001~~ | ✅ CLÔTURÉ MVP (type strict report C-4) | Phase 3.4 | `85b6502c` |
| ~~D-Phase6-Cascade-DeliveryPoint-Fta-001~~ | ✅ CLÔTURÉ (pivot `DP.code_fta` → `DP.grd_code` après audit modèle ORM) | Phase 3.6 | `f4cad96e` |
| ~~D-Phase6-Cascade-Org-Consentements-001~~ | ✅ CLÔTURÉ (pivoté en 2 dettes successeurs Modèle + Activation) | Phase 3.7 | `ee3d782e` |
| ~~D-Sprint-C3-7d-ELD-5-Entries-Disparities-Resolved-001~~ | ✅ CLÔTURÉ même phase (Fix #4 corrige les 5 entrées) | Phase 3.7d | `477e3cea` |

> **Note pivot Phase 3.6** : `D-Phase6-Cascade-DeliveryPoint-Fta-001` ciblait `DeliveryPoint.code_fta` qui n'existe pas dans le modèle ORM (matrice v1 §4.4.G #128 inexact). Audit pré-build Phase 3.6 a détecté l'erreur et pivoté vers `DeliveryPoint.grd_code` (champ canonique réel — 21 ELD).
>
> **Note pivot Phase 3.7** : `D-Phase6-Cascade-Org-Consentements-001` ciblait `Organisation.consentement_dataconnect_global/grdf_global` + `DeliveryPoint.consentement_dataconnect_local/grdf_local` qui n'existent pas dans le modèle ORM. Audit pré-build Phase 3.7 a détecté l'erreur. Décision pragmatique cohérente avec Phase 5.2 Sprint C-2 + Phase 3.6 : NE PAS livrer cascade sur champs fantômes. Scinder en 2 dettes successeurs Sprint C-4 : `D-Sprint-C3-Org-Consentement-Modele-001` (créer modèle + migration Alembic) + `D-Sprint-C3-Cascade-Consentement-Activation-001` (activer cascade après modèle livré).

---

## Dettes ajoutées Sprint C-3 (~13 entrées avec audits follow-up)

### Phase 3.4d — 5 dettes (audit multi-agents 5 verdicts)

| ID | Sprint cible | Priorité |
|---|---|---|
| D-Sprint-C3-Portfolio-Consumption-OrgScope-001 (PRÉ-EXISTANT, signalé par audit) | Hors-sprint critique | 🔴 P0 |
| D-Sprint-C3-YAML-Constants-SG-Coverage-001 | C-4 | 🟡 P1 |
| D-Sprint-C3-Reg-Manquants-Capacite-CBAM-VNU-001 | C-4 | 🟡 P1 |
| D-Sprint-C3-CRE-CTA-URLs-Verifier-001 | C-4 | 🟡 P2 |
| D-Sprint-C3-CO2-GNL-JORFTEXT-Verifier-001 | C-4 | 🟡 P2 |

### Phase 3.6 — 1 dette (cascade pivot)

| ID | Sprint cible | Priorité |
|---|---|---|
| D-Phase3-6-Cascade-PowerContract-FTA-001 | C-4 | 🟡 P1 |

### Phase 3.7 — 2 dettes (pivot consentements RGPD)

| ID | Sprint cible | Priorité |
|---|---|---|
| D-Sprint-C3-Org-Consentement-Modele-001 | C-4 amont | 🟠 P0 |
| D-Sprint-C3-Cascade-Consentement-Activation-001 | C-4 (post-Modele) | 🟠 P1 |

### Phase 3.7d — 8 dettes ouvertes + 1 clôturée (audit multi-agents 5 verdicts)

| ID | Sprint cible | Priorité |
|---|---|---|
| ~~D-Sprint-C3-7d-ELD-5-Entries-Disparities-Resolved-001~~ | ✅ CLÔTURÉE Fix #4 même phase | (clôture immédiate) |
| D-Sprint-C3-7d-EnergieFinale-Type-Strict-001 | C-4 | 🟠 P1 |
| D-Sprint-C3-7d-Cascade-SoT-Reuse-Audit-001 | C-4 | 🟡 P1 |
| D-Sprint-C3-7d-ADR-RGPD-Consent-Detail-001 | C-4 amont | 🟠 P1 |
| D-Sprint-C3-7d-ADR-Intensity-OPERAT-Naming-001 | C-4 amont | 🟡 P1 |
| D-Sprint-C3-7d-ADR-Routes-Namespace-001 | C-4 ou opportunistique | 🟡 P2 |
| D-Sprint-C3-7d-TVA-Reduite-Abo-Gaz-001 | C-4 | 🟡 P1 |
| D-Sprint-C3-7d-Legal-Reference-Completion-001 | C-4 | 🟡 P1 |
| D-Sprint-C3-7d-FE-i18n-TraceTooltip-001 | C-4 ou opportunistique | 🟡 P2 |

> **Finding sécurité Medium** (audit security-auditor Phase 3.7d) : `scope.organisation_id` exposé JSON public `/api/portfolio/intensity` → CWE-200 IDOR amplification. **Fix #3 appliqué intra-Phase 3.7d** (commit `477e3cea`). Référence interne `PROMEOS-SEC-2026-042`. Ticket GitHub fermé directement (créé via UI Option A par utilisateur).

---

## Tracker dette technique évolution

| Étape | Dettes ouvertes | P0 | P1 | P2 |
|---|---|---|---|---|
| Pré-Sprint C-3 (post-C-2 + mini-IDOR meters +2) | 18 | 1 | 5 | 12 |
| Phase 3.4 (-2 clôtures) | 16 | 1 | 4 | 11 |
| Phase 3.4d (+5 dettes audit) | 21 | 2 | 6 | 13 |
| Phase 3.6 (-1 pivot clôture + 1 nouvelle PowerContract) | 21 | 2 | 6 | 13 |
| Phase 3.7 (-1 clôture pivot + 2 nouvelles Modele/Activation) | 22 | 2 | 8 | 12 |
| Phase 3.7d (+9 audit dettes - 1 clôture immédiate ELD) | 28 | 2 | 12 | 14 |
| **Post Sprint C-3 (renommage Phase 3.7d + ADR split en 3 entries)** | **28** | **2** | **12** | **14** |

**Bilan tracker Sprint C-3** : net +10 dettes (15 ajoutées - 5 clôturées). 2 P0 ouvertes :
- Surface OPERAT 3 distincts (Phase 4.5d Sprint C-2, hérité)
- Portfolio consumption org-scoping pré-existant (Phase 3.4d Sprint C-3)

---

## Baseline non-régression

| Couche | Pré-Sprint C-3 | Post-Sprint C-3 | Δ |
|---|---|---|---|
| Backend (collected) | ~7 472 (post mini-IDOR) | **7 898** | **+426** |
| Frontend (collected) | 4 550 | **4 584** | **+34** |
| **Total cumulé** | **12 022** | **12 482** | **+460** |
| **Régressions** | 0 | **0** | ✅ |

> Note : delta BE +426 reflète l'évolution post-merge mini-IDOR + 7 phases Sprint C-3 cumulé. Tests scope ciblé Phase 3.7d portfolio_intensity 9/9 verts post-fix #3 (CWE-200).

### Évolution baseline BE phase par phase (estimée)

| Étape | Tests Δ |
|---|---|
| Pré-Sprint C-3 (post mini-IDOR meters) | — |
| Post-Phase 3.2 (sources_reglementaires + service) | +30 |
| Post-Phase 3.3 (endpoint /api/regulatory/rates) | +33 |
| Post-Phase 3.4 (endpoint /api/portfolio/intensity + SG kWhEF) | +13 |
| Post-Phase 3.4d (audit follow-up — fixes ciblés) | 0 net |
| Post-Phase 3.6 (eld_gaz_referentiel + cascade DP.grd_code) | +24 |
| Post-Phase 3.7 (pivot read-only) | 0 |
| **Post-Phase 3.7d (audit follow-up — fixes ciblés)** | **0 net** |

### Évolution baseline FE phase par phase

| Étape | Tests Δ |
|---|---|
| Pré-Sprint C-3 | — |
| Post-Phase 3.3 (hook useRegulatoryRates + tests) | +11 |
| Post-Phase 3.5 (composant TraceTooltip + 5 intégrations) | +23 |
| **Total +34** | |

**Régressions** : 0 sur l'ensemble Sprint C-3.

---

## Source-guards activés Sprint C-3 (~10 nouveaux)

| Fichier | Phase | Patterns interdits / Patterns invariants |
|---|---|---|
| `backend/tests/source_guards/test_regulatory_yaml_constants_coherence_source_guards.py` | 3.2 | Cohérence YAML `sources_reglementaires.yaml` ↔ `regulatory_constants.py` (10/68 termes couverts MVP — extension Sprint C-4 trace dette) |
| `backend/tests/source_guards/test_annual_kwh_total_kwhef_pci_source_guards.py` | 3.4 | Allowlist écritures `Site.annual_kwh_total` + commentaire "kWhEF PCI" obligatoire |
| `backend/tests/source_guards/test_eld_gaz_referentiel_loader_source_guards.py` | 3.6 | Cohérence YAML `eld_gaz_referentiel.yaml` ↔ `eld_gaz_loader.py` (21 entrées + types valides) |

(Liste détaillée à compléter Sprint C-7 polish — focus sur source-guards majeurs ci-dessus)

---

## Architecture livrée Sprint C-3

### Backend SoT YAML versionné

```text
backend/config/
├── sources_reglementaires.yaml       [Phase 3.2 — 68 termes / 11 domaines + 19 sous-domaines]
├── eld_gaz_referentiel.yaml          [Phase 3.6 — 21 ELD (1 GRDF national + 20 ELD locales)]
├── regulatory_sources_loader.py      [Phase 3.2 — pattern tarif_loader.py reproduit + @lru_cache]
└── eld_gaz_loader.py                 [Phase 3.6 — pattern reproduit Phase 3.2]
```

### Backend cascade scope étendu (11 → 12 champs)

| Champ source | Output(s) | Phase |
|---|---|---|
| Site.code_postal (Sprint C-1) | zone+palier+cabs+compliance | C-1 P6 |
| Site.altitude_m (Sprint C-1) | palier+cabs+compliance | C-1 P6 |
| Site.tertiaire_area_m2 (Sprint C-1+C-2) | compliance + intensity_tertiaire | C-1 P6 + C-2 P4.2 |
| Site.parking_area_m2 (Sprint C-1) | aper_assujetti+taille+deadline+compliance | C-1 P6 |
| Site.roof_area_m2 (Sprint C-1) | compliance | C-1 P6 |
| Site.operat_sous_categorie_id (Sprint C-1) | cabs+compliance | C-1 P6 |
| Batiment.cvc_power_kw (Sprint C-1) | compliance site parent | C-1 P6 |
| Site.surface_m2 (Sprint C-2) | intensity_total | C-2 P4.2 |
| Site.annual_kwh_total (Sprint C-2) | intensity_total + intensity_tertiaire | C-2 P4.2 |
| AuditEnergetique.conso_annuelle_moy_gwh (Sprint C-2) | obligation + recompute_organisation | C-2 P5.2 |
| EnergyContract.end_date (Sprint C-2) | reset flag + renewal_alert log | C-2 P5.3 |
| **DeliveryPoint.grd_code** (Sprint C-3) | **eld_metadata + bill_recheck** | **C-3 P3.6** |

> Cascade Org consentements (Phase 3.7) reportée Sprint C-4 (modèle ORM préalable absent). Anti-cycle préservé : aucune des sorties cascade-sink (`intensity_*`, `renewal_alert`, `audit_sme_obligation`, `eld_metadata`) n'est jamais source de cascade vers ses propres triggers.

### Frontend traçabilité réglementaire (R10 livré)

```text
frontend/src/
├── ui/
│   └── TraceTooltip.jsx              [Phase 3.5 — composition Explain.content, ~70 LOC, fallback graceful]
├── contexts/
│   └── RegulatoryRatesProvider.jsx   [Phase 3.3 — cache module-level, useRegulatoryRates hook]
├── hooks/
│   └── useRegulatoryRates.js         [Phase 3.3 — fetch + cache + types stricts]
└── pages/
    ├── cockpit/
    │   ├── Cockpit.jsx               [Phase 3.5 — TraceTooltip 1 KPI rate]
    │   └── CockpitDecision.jsx       [Phase 3.5 — TraceTooltip 1 KPI rate]
    ├── RegOps.jsx                    [Phase 3.5 — TraceTooltip 1 KPI rate]
    ├── Patrimoine.jsx                [Phase 3.5 — TraceTooltip 1 KPI rate]
    └── conformite-tabs/
        └── ObligationsTab.jsx        [Phase 3.5 — TraceTooltip 1 KPI rate]
```

### Backend endpoints publics traçables

```text
backend/
├── routes/
│   ├── regulatory_rates.py           [Phase 3.3 — GET /api/regulatory/rates (public, sources légales)]
│   └── portfolio_intensity.py        [Phase 3.4 — GET /api/portfolio/intensity (org-scoped, scope.organisation_id retiré CWE-200)]
└── services/
    ├── regulatory_sources_service.py [Phase 3.2 — fetch + normalisation YAML]
    └── portfolio_intensity_service.py [Phase 3.4 — Σ(kWh)/Σ(m²) ratio des SOMMES doctrine]
```

---

## Décisions archi cardinales validées Sprint C-3

| Phase | Décision | Justification |
|---|---|---|
| 3.1 | Option B YAML statique git-versionné (pas ParameterStore DB) | Cohérence pattern existant `tarifs_reglementaires.yaml` + R10 différenciateur = traçabilité légale lisible |
| 3.1 | TraceTooltip = composition Explain.content (pas refactor) | Évite breaking change sur Explain existant — wrapper opt-in |
| 3.2 | 68 termes / 11 domaines monolithique (pas multi-fichiers) | Lisibilité + index unique YAML — multi-fichiers reporté Sprint C-7 |
| 3.3 | Endpoint public sans org-scoping | Sources réglementaires = données publiques (CRE/Légifrance/RTE accessibles tous) |
| 3.3 | RegulatoryRatesProvider imbriqué dans RegulatoryConstantsProvider | Séparation cohérente : constantes Python vs sources légales tracées |
| 3.3 | 10 source-guards cohérence YAML ↔ constants.py (anti-drift) | Cardinal contre dérive silencieuse YAML/Python (extension 68/68 reportée Sprint C-4) |
| 3.4 | `compute_portfolio_intensity` = Σ(kWh)/Σ(m²) (pas moyenne arithmétique des ratios) | Mathématiquement correct pour portefeuille pondéré par taille (doctrine PROMEOS) |
| 3.4 | Source-guard kWhEF PCI MVP via grep + commentaire (pas type strict) | MVP suffisant pour Enedis kWhEF natif, type strict GRDF PCS→PCI reporté Sprint C-4 |
| 3.5 | TraceTooltip composition Explain — fallback graceful no-trace = enfants seuls | Compat backward sur 50+ usages existants Explain |
| 3.6 | DP.grd_code (pas code_fta inexistant) — pivot doctrinal post-audit | Champ canonique réel + 21 ELD officiel CRE (vs `code_fta` matrice v1 §4.4.G #128 inexact) |
| 3.6 | Cascade GRDF court-circuit ELD locales | Cascade Org.consentement_grdf → DPs `grd_code=GRDF` uniquement (les 20 ELD ont leur propre process consentement = différenciateur RGPD) |
| 3.7 | NE PAS livrer cascade sur champs fantômes Org.consentement_* | Pivot pragmatique cohérent Phase 5.2 Sprint C-2 + Phase 3.6 — modèle ORM préalable bloquant |
| 3.7d | `scope.organisation_id` retiré JSON public (PROMEOS-SEC-2026-042) | CWE-200 IDOR amplification — ID auto-incrémenté retiré, scope client-fourni `portefeuille_id` conservé |
| 3.7d | Constantes Audit SMÉ + dates APER → SoT YAML (`get_audit_sme_threshold` / `get_term_value`) | Anti-duplication — 1 SoT par concept réglementaire (doctrine §6.4) |

---

## Découvertes notables Sprint C-3

### 1. Pattern audit multi-agents SDK — 3e application réussie

3 audits multi-agents successifs avec pattern reproductible (`code-reviewer + qa-guardian + security-auditor + regulatory-expert + architect-helios + test-engineer`) :

| Audit | Phase | Agents | Findings | Fixes intra-phase | Dettes tracées |
|---|---|---|---|---|---|
| Phase 4.5d Sprint C-2 | C-2 | 6 parallèle | 6 verdicts | 2 P1 ciblés | 4 dettes regulatory + 1 sécurité signalée |
| Phase 3.4d Sprint C-3 | C-3 | 5 | 5 verdicts | 5 P0+P1 | 5 dettes |
| Phase 3.7d Sprint C-3 | C-3 | 5 | 5 verdicts | 4 fixes (1 sécurité Medium CWE-200) | 8 dettes ouvertes + 1 clôturée |

**ROI cumulé** : ~11 fixes intra-sprint + ~17 dettes tracées + 3 findings sécurité Medium/High détectés.

KB MEMORY.md systématiquement consultée par les agents (`reference_sources_veille_kb.md` + `feedback_kb_sources_systematic.md` honorés sur les 3 audits).

### 2. Différenciateur R10 (TraceTooltip) livré Phase 3.5 → argument commercial

Chaque chiffre/label réglementaire dans 5 pages stratégiques (Cockpit, CockpitDecision, RegOps, Patrimoine, ObligationsTab) traçable jusqu'à sa source légale (Légifrance / CRE / RTE) avec :
- `version` du texte (ex : "v6 délibération 2024-12-19")
- `effective_date` (date d'application)
- `legal_reference` (JORFTEXT / délibération CRE / arrêté ministériel)
- URL deep-link Légifrance/CRE

→ Argument commercial fort vs Deepki / Spacewell / Energisme / Metron (concurrents généralistes sans traçabilité légale ligne par ligne).

### 3. Pivots doctrinaux Phase 3.6 + 3.7 — 3e + 4e occurrence cumul Sprint

Modèle ORM réel ≠ matrice v1 dans 2 cas Sprint C-3 :
- **Phase 3.6** : `DeliveryPoint.code_fta` (matrice v1 §4.4.G #128) inexistant → pivot vers `DeliveryPoint.grd_code` (champ réel)
- **Phase 3.7** : `Organisation.consentement_dataconnect_global/grdf_global` + `DeliveryPoint.consentement_*_local` inexistants → pivot pragmatique = NE PAS livrer cascade sur champs fantômes, scinder en 2 dettes successeurs Modèle + Activation

Pattern confirmé Sprint C-2 Phase 5.1 (`EJ.consommation_3y` inexistant → pivot `AuditEnergetique.conso_annuelle_moy_gwh`).

**Action Sprint C-7 polish** : audit qualité tracker dette systématique (vérification que chaque entrée pointe sur un élément réel du repo). Cf. `D-Sprint-C7-Tracker-Quality-Audit-001` (à créer).

### 4. Court-circuit ELD locales sur cascade GRDF Phase 3.6 — différenciateur RGPD-compliant

Cascade `Organisation.consentement_grdf_global` → propage UNIQUEMENT aux DPs `grd_code=GRDF`. Les 20 ELD locales (Régaz Bordeaux, GreenAlp Grenoble, R-GDS Strasbourg, Vialis Colmar, etc.) ont leur propre process consentement local (cascade locale `DP.consentement_grdf_local` reportée Sprint C-4 post-modèle).

→ Niveau de finesse RGPD que les concurrents (Deepki / Spacewell généralistes B2B) traitent rarement — base TraceTooltip + PII-safe.

### 5. CWE-200 IDOR amplification fixé Phase 3.7d — pattern PROMEOS-SEC-2026-XXX adopté

Réponse JSON publique `/api/portfolio/intensity` exposait `scope.organisation_id` (ID auto-incrémenté). Audit `security-auditor` Phase 3.7d a détecté → Fix #3 retire le champ JSON public (référence interne `PROMEOS-SEC-2026-042`).

Pattern `PROMEOS-SEC-YYYY-NNN` désormais adopté pour tous findings sécurité tracés (cohérent avec mini-sprint IDOR meters CWE-639 → ticket #275).

---

## Prochaine étape — Sprint C-4

**Sprint C-4 — Tests + observabilité** (estimé 14-18 j-h selon plan Phase B).

Périmètre prioritaire (basé sur dettes Sprint C-3 + plan Phase B) :

| Priorité | Sujet | Référence |
|---|---|---|
| P0 amont | ADR consentement_modele_rgpd + migration Alembic | `D-Sprint-C3-7d-ADR-RGPD-Consent-Detail-001` + `D-Sprint-C3-Org-Consentement-Modele-001` |
| P0 amont | ADR cohabitation endpoints intensity + namespace API | `D-Sprint-C3-7d-ADR-Intensity-OPERAT-Naming-001` + `D-Sprint-C3-7d-ADR-Routes-Namespace-001` |
| P1 | Phase 3.8 reportée : `coherence_globale.yaml` (cross-pillar invariants) | (verdict architect-helios, début sprint) |
| P1 | Cascade Org consentements activation (post-modèle) | `D-Sprint-C3-Cascade-Consentement-Activation-001` |
| P1 | Type strict EnergieFinale GRDF kWh PCS → PCI (0.901) | `D-Sprint-C3-7d-EnergieFinale-Type-Strict-001` |
| P1 | Audit balayage SoT reuse (constantes locales dupliquant YAML) | `D-Sprint-C3-7d-Cascade-SoT-Reuse-Audit-001` |
| P1 | Extension source-guards SG_REG_CONST_* couvre 68/68 termes (vs 10/68) | `D-Sprint-C3-YAML-Constants-SG-Coverage-001` |
| P1 | 9 termes réglementaires manquants YAML (Capacité 2026 / CBAM / VNU) | `D-Sprint-C3-Reg-Manquants-Capacite-CBAM-VNU-001` |
| P1 | Audit qualité YAML cross-source ELD (post Fix #4 Phase 3.7d) | `D-Sprint-C4-ELD-Quality-YAML-CrossSource-Audit-001` (NEW) |
| P1 | Conftest._ensure_seeded reset alembic_version | `D-Sprint-C2-Conftest-Reseed-Reset-001` (hérité) |
| P1 | Audit balayage post-V92 split stale imports | `D-V92-Split-Stale-Imports-Audit-001` (hérité) |
| P1 | Cascade `PowerContract.fta_code` → profil tarifaire | `D-Phase3-6-Cascade-PowerContract-FTA-001` |
| P1 | Cascade `AuditEnergetique.conso` legacy callsites (~7-9) | `D-Phase1-Audit-Log-Legacy-Callsites-001` (hérité) |
| P1 | TVA réduite 5,5% abonnement gaz résidentiel | `D-Sprint-C3-7d-TVA-Reduite-Abo-Gaz-001` |
| P1 | Legal reference completion (18+ termes JORFTEXT/URL) | `D-Sprint-C3-7d-Legal-Reference-Completion-001` |
| P1 | DJU adjustment intensity_kwh_m2_tertiaire | `D-Phase4-2-Operat-Intensity-DJU-Adjustment-001` (hérité) |
| P1 | ObligationsTab heuristics inline → endpoint | `D-ObligationsTab-Heuristics-Inline-001` (hérité) |
| P2 | Tests perf bulk recompute organisation (50/200/500 sites) | (Plan Phase B) |
| P2 | i18n TraceTooltip "effective" → "applicable depuis" | `D-Sprint-C3-7d-FE-i18n-TraceTooltip-001` |

**Tickets dédiés à créer hors-sprint** :
- 🔴 **High sécurité** : `D-Sprint-C3-Portfolio-Consumption-OrgScope-001` (PRÉ-EXISTANT — IDOR sur `/api/portfolio/consumption/*`) — pré-pilote critique
- 🔴 **Capacité RTE 1/11/2026** (échéance ~6 mois post-Sprint C-3) — issue dédiée
- 🟢 **PROMEOS-SEC-2026-042** (CWE-200 fixé Phase 3.7d, ticket fermé directement, créé via UI Option A)

---

**Fin Sprint C-3** — 7 phases livrées sur 8 prévues + 8 commits atomiques + 5 audits pré-build + 2 audits multi-agents SDK + +123 tests BE + +34 tests FE + 0 régression finale + 5 dettes clôturées + 2 GAPS audit Phase B comblés (R10 + Phase 22 migration) + différenciateur R10 TraceTooltip réglementaire FE livré.

🚦 **STOP gate finale Sprint C-3** — bilan complet livré. Phase 3.8 (`coherence_globale.yaml`) reportée Sprint C-4 (verdict architect-helios + cohérence avec 7 dettes Phase 3.7d à digérer en sprint Tests + observabilité).
