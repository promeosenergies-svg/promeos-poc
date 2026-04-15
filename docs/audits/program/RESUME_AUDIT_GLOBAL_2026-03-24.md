# RÉSUMÉ AUDIT GLOBAL PROMEOS — 24 mars 2026 (v3)

> Document de continuité. Synthèse complète de toutes les étapes d'audit et corrections.
> Référence unique pour les prochaines étapes.

---

## 1. ÉTAT DES LIEUX

| | |
|---|---|
| **Note départ (23/03)** | 6.5 / 10 |
| **Après audit approfondi** | 7.0 / 10 (3 faux P0 invalidés) |
| **Après corrections étape 3+4bis** | 7.5 / 10 |
| **Après sprint XS P0** | 8.3 / 10 |
| **Après sprint S P0-2 (24/03)** | **8.6 / 10** |
| **Note cible 90 jours** | 9.0 / 10 |

**0 P0 restant.** Tous les bloquants crédibilité sont fermés.

---

## 2. ÉTAPES D'AUDIT RÉALISÉES

| Étape | Fichier | Statut |
|---|---|---|
| **0 — Cadrage** | `AUDIT_PROMEOS_ETAPE_00_CADRAGE_2026-03-23.md` | ✅ |
| **1 — Fil conducteur** | `AUDIT_PROMEOS_ETAPE_01_FIL_CONDUCTEUR_2026-03-23.md` | ✅ |
| **2 — Règles métier** | `AUDIT_PROMEOS_ETAPE_02_REGLES_METIER_CONFORMITE_2026-03-23.md` | ✅ |
| **3 — Bill Intelligence** | `AUDIT_PROMEOS_ETAPE_03_BILL_INTELLIGENCE_ACHAT_2026-03-23.md` | ✅ |
| **3 — Fix** | `FIX_PROMEOS_ETAPE_03_BILL_INTELLIGENCE_ACHAT_2026-03-23.md` | ✅ |
| **3 — Verify** | `VERIFY_PROMEOS_ETAPE_03_BILL_INTELLIGENCE_ACHAT_2026-03-23.md` | ✅ |
| **3B — PurchaseAssistant** | `FIX_PROMEOS_ETAPE_03B_PURCHASE_ASSISTANT_2026-03-23.md` | ✅ |
| **4 — Conformité→Facture→Actions** | `AUDIT_PROMEOS_ETAPE_04_CONFORMITE_FACTURE_ACTIONS_2026-03-23.md` | ✅ |
| **4bis — Conso/Performance** | `AUDIT_PROMEOS_ETAPE_04BIS_CONSO_PERFORMANCE_2026-03-23.md` | ✅ |
| **Sprint XS P0** | `FIX_PROMEOS_SPRINT_XS_P0_2026-03-24.md` | ✅ |
| **Sprint S P0-2** | `FIX_PROMEOS_SPRINT_S_P0_2_CONFORMITE_FACTURE_2026-03-24.md` | ✅ |

---

## 3. CORRECTIONS APPLIQUÉES (20 total)

### Étape 3 — Bill Intelligence & Achat (6)

| # | Correction | Statut |
|---|---|---|
| 1 | Prix par défaut : source unique `config/default_prices.py` | ✅ |
| 2 | Dépréciation moteur achat simple | ✅ |
| 3 | TICGN versionnée (3 entrées temporelles) | ✅ |
| 4 | PurchaseAssistant `_computation_note` visible | ✅ |
| 5 | Auto-sync actions achat à l'ouverture d'ActionsPage | ✅ |
| 6 | Bannière données marché démo | ✅ |

### Étape 3B — PurchaseAssistant (3)

| # | Correction | Statut |
|---|---|---|
| 7 | `USE_BACKEND_PRICING` câblé | ✅ |
| 8 | Fallback dégradé honnête | ✅ |
| 9 | Wording distinct serveur/local/dégradé | ✅ |

### Étape 4bis — Alignement Conso/Performance (4)

| # | Correction | Statut |
|---|---|---|
| 10 | CO₂ : 0.0569 → 0.052 (ADEME Base Empreinte V23.6, vérifié ×3) | ✅ |
| 11 | `co2_service.py` : `Compteur` → `Meter` (modèle Yannick) | ✅ |
| 12 | `compliance_engine.py` M&V : `Consommation` → `MeterReading` | ✅ |
| 13 | Import mort `Compteur` supprimé de compliance_engine | ✅ |

### Sprint XS P0 (4)

| # | Correction | Statut |
|---|---|---|
| 14 | KPI DT dynamique : `update_site_avancement()` câblé dans `recompute_site_full()` | ✅ |
| 15 | BACS 70kW : `regs.yaml:66` corrigé 2027 → 2030 (décret n°2025-1343) | ✅ |
| 16 | DPE/CSRD : marqués `implemented: false` dans regs.yaml | ✅ |
| 17 | CVC déterministe : `random.uniform()` → médiane `(lo+hi)/2` | ✅ |

### Sprint S P0-2 — Conformité ↔ Facture (3)

| # | Correction | Statut |
|---|---|---|
| 18 | **BillIntelPage** : bandeau amber + CTA "Voir conformité →" si anomalies critiques | ✅ |
| 19 | **ConformitePage** : CTA "Vérifier les factures →" à côté du badge risque financier | ✅ |
| 20 | **Cockpit** : `billing_anomalies_eur` scopé (exclut resolved + false_positive) | ✅ |

---

## 4. P0 / P1 / P2 RESTANTS

### P0 — Bloquant crédibilité

| # | Problème | Statut |
|---|---|---|
| ~~P0-1~~ | ~~KPI DT = champ plat~~ | ✅ Corrigé |
| ~~P0-2~~ | ~~Conformité ↔ Facture = aucun lien~~ | ✅ Corrigé |
| ~~P0-3~~ | ~~regs.yaml BACS 70kW = 2027~~ | ✅ Corrigé |

**0 P0 restant.**

### P1 — Crédibilité marché

| # | Problème | Effort | Statut |
|---|---|---|---|
| P1-1 | Scénarios achat = price_factor fixe (1.05/0.95/0.88) | L | ❌ |
| ~~P1-2~~ | ~~CVC estimation aléatoire~~ | ~~XS~~ | ✅ Corrigé |
| ~~P1-3~~ | ~~Scoring YAML 5 fw sans flag implemented~~ | ~~XS~~ | ✅ Corrigé |
| P1-4 | APER sans obligations ni preuves structurées | M | ❌ |
| P1-5 | Confidence non affichée dans badges UI | S | ❌ |
| ~~P1-6~~ | ~~Cockpit billing_anomalies_eur hardcodé 0~~ | ~~S~~ | ✅ Corrigé |

### P2 — Premium

| # | Problème | Effort | Statut |
|---|---|---|---|
| P2-1 | Breakdown DT/BACS/APER non affiché systématiquement | S | ❌ |
| P2-2 | Benchmark sectoriel ADEME/OID | L | ❌ |
| P2-3 | Risque financier sans label "théorique maximum" | XS | ❌ |

---

## 5. SOURCES DE VÉRITÉ ÉTABLIES

| Domaine | Fichier | Valeur |
|---|---|---|
| Prix par défaut | `config/default_prices.py` | 0.18 EUR/kWh élec, 0.09 gaz |
| CO₂ élec | `config/emission_factors.py` | 0.052 kgCO₂e/kWh (ADEME V23.6) |
| CO₂ gaz | `config/emission_factors.py` | 0.227 kgCO₂e/kWh (ADEME V23.6) |
| TURPE 7 | `billing_engine/catalog.py` | CRE n°2025-78, 01/08/2025 |
| TICGN | `billing_engine/catalog.py` | 3 entrées temporelles versionnées |
| Compteurs/Conso | `Meter` + `MeterReading` | Périmètre Yannick (lecture seule) |
| Scoring conformité | `compliance_score_service.py` | A.2 : DT 45% + BACS 30% + APER 25% |
| BACS deadlines | `regulations/bacs/v2.yaml` + `regs.yaml` | 290kW→2025, 70kW→2030 |

---

## 6. PÉRIMÈTRE YANNICK — LECTURE SEULE

> **On ne touche PAS au travail de Yannick. On l'exploite en lecture.**

| Zone protégée |
|---|
| `MonitoringPage.jsx` (3112L) |
| `useExplorerMotor.js` |
| `electric_monitoring/` (5 engines) |
| `consumption_diagnostic.py` (939L) |
| `gen_readings.py` |
| `ems/*.py` (3 services) |
| `consumption_unified_service.py` |
| `consumption_context_service.py` |
| `frontend/src/pages/consumption/` (37 panels) |

---

## 7. CONFLITS IDENTIFIÉS ET TRAITÉS

| # | Conflit | Statut |
|---|---|---|
| C1 | CO₂ 0.0569 vs 0.052 | ✅ Corrigé → 0.052 |
| C2 | `co2_service.py` query `Compteur` | ✅ Corrigé → `Meter` |
| C2b | `compliance_engine.py` M&V query `Consommation` | ✅ Corrigé → `MeterReading` |
| C3 | 3 moteurs DQ parallèles | ℹ️ Design légitime |
| C4 | `alert_engine.py` HORS_HORAIRES = 7h-19h fixe | ⚠️ Signalé Yannick |
| C5 | `Compteur` dans patrimoine services | ℹ️ CRUD légitime |
| C6 | `ConsumptionSource` enum manque `ESTIMATED` | ℹ️ Cosmétique |

---

## 8. SOURCES RÉGLEMENTAIRES VÉRIFIÉES (×2 minimum)

| Point | Source officielle | Valeur | Certitude |
|---|---|---|---|
| BACS 70kW | [Décret n°2025-1343](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053175245) + [Art. R175-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000053216492) | **2030-01-01** | Confirmé ×2 |
| DT seuil | [Art. R174-22 CCH](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043819501) | **1000 m²** | Confirmé |
| DT trajectoire | [Art. L174-1 CCH](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043977483) | **-40/-50/-60%** | Confirmé |
| TURPE 7 | [CRE n°2025-78](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195) + [Enedis](https://www.enedis.fr/media/4717/download) | 01/08/2025 | Confirmé ×2 |
| CO₂ élec | ADEME Base Empreinte V23.6 + RTE BE2024 + Bilans GES | **0.052 kgCO₂e/kWh** | Confirmé ×3 |
| APER parking | [Art. 40 Loi n°2023-175](https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000047294291) + [Décret n°2024-1023](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050495478) | ≥1500m² | Confirmé ×2 |
| TICGN fév 2026 | Art. 265 Code des douanes consolidé | 0.01073 EUR/kWh | Confirmé |

---

## 9. SCORE PAR AXE (mis à jour 24/03 soir)

| Axe | Note | Évol. | Justification |
|---|---|---|---|
| Produit / logique | **8/10** | +1.0 | KPI DT dynamique, conformité↔facture liées, fil conducteur complet |
| UX / UI | **7.5/10** | +0.5 | Bandeau risque dans BillIntel, CTA croisés, scope préservé |
| Front | **7.5/10** | = | Composants solides, pas de changement structural |
| Back / API | **8.5/10** | = | Sources unifiées, Meter aligné, configs fiables |
| Données / Modèle métier | **7.5/10** | = | CO₂ unifié, Meter source de vérité, CVC déterministe |
| Règles métier / conformité | **8/10** | = | BACS corrigé, DPE/CSRD flaggés, KPI DT câblé |
| Facturation / achat | **7/10** | +0.5 | billing_anomalies_eur scopé, lien conformité↔facture |
| Multi-sites / navigation | **7.5/10** | = | ScopeContext 3 niveaux, breadcrumb, drill-down |
| Crédibilité marché | **7.5/10** | +0.5 | Config réglementaire fiable, lien conformité↔facture crédible |

---

## 10. FICHIERS MODIFIÉS (cumulé, 20 corrections)

### Backend (14 fichiers)

| Fichier | Correction |
|---|---|
| `config/emission_factors.py` | CO₂ 0.052 (ADEME V23.6) |
| `config/default_prices.py` | Source unique prix |
| `services/co2_service.py` | `Compteur` → `Meter` |
| `services/compliance_engine.py` | M&V → `MeterReading`, import mort supprimé |
| `services/compliance_coordinator.py` | Étape 1b : `update_site_avancement()` |
| `services/billing_service.py` | Prix unifié |
| `services/purchase_scenarios_service.py` | Marqué DÉPRÉCIÉ |
| `services/onboarding_service.py` | CVC déterministe |
| `services/billing_engine/catalog.py` | TICGN versionnée |
| `services/billing_shadow_v2.py` | TICGN depuis catalog |
| `services/purchase_pricing.py` | `source` + `is_demo` |
| `routes/contracts_radar.py` | `_deprecated` dans réponse |
| `routes/cockpit.py` | `billing_anomalies_eur` scopé (excl. resolved/false_positive) |
| `regops/config/regs.yaml` | BACS 2030, DPE/CSRD `implemented: false` |

### Frontend (7 fichiers)

| Fichier | Correction |
|---|---|
| `pages/BillIntelPage.jsx` | Bandeau risque + CTA "Voir conformité →" |
| `pages/ConformitePage.jsx` | CTA "Vérifier les factures →" |
| `pages/PurchaseAssistantPage.jsx` | Backend pricing, fallback, wording |
| `pages/ActionsPage.jsx` | Auto-sync actions |
| `components/purchase/MarketContextBanner.jsx` | Badge démo |
| `ui/glossary.js` | CO₂ 0.052, source V23.6 |
| `__tests__/step4_co2_guard.test.js` | Guards alignés |

### Tests vérifiés

| Suite | Résultat |
|---|---|
| `test_emissions.py` + `test_compliance_v68.py` | 41/41 ✅ |
| `test_billing.py` | 40/40 ✅ |
| `step4_co2_guard.test.js` | 9/9 ✅ |
| CVC déterminisme | ✅ |
| regs.yaml parse (BACS = 2030) | ✅ |
| Imports cockpit + co2 + compliance | ✅ |

---

## 11. PROCHAINES ÉTAPES

### P1 prioritaires

| # | Action | Impact | Effort |
|---|---|---|---|
| 1 | Scénarios achat dynamiques (prix marché simplifié) | +0.3 | L |
| 2 | APER obligations auto-créées + preuves structurées | +0.2 | M |
| 3 | Confidence affichée dans badges conformité | +0.1 | S |

### Audits restants

| Étape | Focus |
|---|---|
| **5 — UX/UI sévère** | Lisibilité, densité, cohérence visuelle, démo-readiness |
| **6 — Front technique** | Composants, dette, performance, responsive |
| **7 — Tests & QA** | Couverture, smoke tests, E2E, régression |
| **8 — Go-to-market** | Pitch, démo, crédibilité marché, vendabilité |

---

*Résumé consolidé v3 — 24 mars 2026. 0 P0 restant. 20 corrections appliquées. 8.6/10.*
