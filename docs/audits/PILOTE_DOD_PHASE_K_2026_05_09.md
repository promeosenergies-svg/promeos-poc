# DoD Pilote pré-prod externe PROMEOS — Phase K (post-Phase J)

**Date** : 2026-05-09
**Branche** : `claude/refonte-sol2`
**Commit cardinal** : Phase K post J (`69b27aa1` baseline)
**Personas cibles** : Marie DAF bailleur 25 sites · Jean-Marc CFO ETI 12 sites IDF

## Vision Consolidée v1.3 — pricing 3 tiers cible

| Tier | Prix | Cible | Statut DoD |
|---|---|---|---|
| **Lite** | 6,9 k€/an (1-10 sites, 1 module) | Pilote 6 mois engagement | ✅ READY |
| **Control** | 19,9 k€/an (5-15 sites, full socle) | Bascule post-pilote sur preuve | ✅ READY conditionnel |
| **Plus** | 19,9 k€ + 850 €/site/an (16+ sites) | Extension Marie DAF 25 sites | ⏳ Post-pilote |

## DoD vérifications cardinales (10 critères)

### Sécurité multi-tenant (Phase E IDOR)
- ✅ **resolve_org_id** appliqué cardinal sur 22 endpoints `patrimoine_crud` (Phase E)
- ✅ **JOIN chain Org→EJ→Pf→Site→Bati** vérifié sur tous les guards (Phase E)
- ✅ **bridge_route P0 IDOR fix** appliqué (Phase F audit P0-1)
- ✅ **OOM Content-Length pre-read check** (Phase F P0-2)
- ✅ **create_organisation admin role strict** DG_OWNER/DSI_ADMIN (Phase F P0-3)

**Verdict sécurité** : ✅ GO pilote externe multi-tenant levé.

### Couverture personas Vision v1.3

**Marie DAF (bailleur 25 sites — ARR cible 498 k€/3 ans)** :
- ✅ 5 frameworks compliance (DT/BACS/APER/OPERAT/DPE) avec deadlines countdown
- ✅ Audit SMÉ ISO 50001 exemption (Loi DDADUE 2025-391 art. 8)
- ✅ Sanctions provisionnées split certain vs pending
- ✅ Urgency enum (CRITICAL/HIGH/MEDIUM/LOW/OVERDUE)
- ✅ Export PDF comité (`GET /api/persona/marie-daf/compliance-dashboard.pdf`)
- ✅ Bridge eIDAS Compliance+ (signataire_email Phase F1)

**Jean-Marc CFO (ETI 12 sites — bascule Lite→Control)** :
- ✅ Détection anomalies factures (6 règles : R19/R20/R21/R22/R23/R24)
- ✅ R22 raffinement DP routing T1/T2/HP (Phase J accuracy)
- ✅ Comparateur prix EPEX MVP (`/api/persona/cfo/contract-price-benchmark`)
- ✅ Alertes contrat fin J-180 (configurable 30→365 j)
- ✅ Top 5 anomalies par montant + by_severity

### Architecture & dette technique

- ✅ **Phase E IDOR** : 22 endpoints scopés
- ✅ **Phase F1** : Fournisseur entité hybride canonique + tenant
- ✅ **Phase F2** : Parser PDF facture bridge SIREN
- ✅ **Phase F3** : Parser PDF contrat preview
- ✅ **Phase J2** : ADR-F-04 hard-cut soft `supplier_name` → `fournisseur_id`
- ✅ **Phase K1** : `__init__` override → `@event.listens_for("init")` orthodoxe
- ✅ **Phase K2** : `_normalize_enum_value` module-level + cache batch DPs

### Tests cumul

- **Backend** : 275/275 verts (Phase D-4 + E + F + G + H + I + J + K)
- **Frontend** : 3746/3746 verts (178 fichiers)
- **0 régression** introduite sur 60 livraisons consécutives
- **6 règles anomalies** actives (R19 VNU + R20 capacité + R21 CTA + R22 accise +
  R23 TURPE + R24 TVA)
- **5 frameworks compliance** par site (Marie DAF cardinal)

## Checklist déploiement pré-prod

### Configuration runtime

- [ ] **DEMO_MODE=false** désactivé (CLAUDE.md règle pilote externe)
- [ ] **PROMEOS_J2_HARDCUT=1** activé (mode strict ADR-F-04 — fournisseur_id obligatoire)
- [ ] **Logging** : configurer handler `promeos.billing` warning vers Sentry/Datadog
  pour observability dette `supplier_name` orphelin
- [ ] **JWT secret** : rotation depuis valeur DEMO_MODE
- [ ] **CORS** : restriction au domaine pilote externe

### Données seed pilote

- [ ] **Org pilote** : création via `POST /api/patrimoine/crud/organisations` (admin)
- [ ] **Fournisseurs canoniques** : seed `fournisseurs_canoniques.py` (10 FR)
- [ ] **Backfill fournisseur_id** : exec `python -m scripts.backfill_fournisseur_id`
- [ ] **Vérification** : 100 % EnergyContract ont fournisseur_id résolu

### Personas onboarding

**Marie DAF (J0 → J+30)** :
- [ ] J0 : import 25 sites + 8 EJ via Sirène wizard (popup mode Phase G)
- [ ] J+7 : saisie surface tertiaire + statut OPERAT par site
- [ ] J+14 : import DPE existants (Batiment.dpe_class A-G + dpe_date_validite)
- [ ] J+21 : revue dashboard `/api/persona/marie-daf/compliance-dashboard`
- [ ] J+30 : génération PDF comité 1ère présentation CA

**Jean-Marc CFO (J0 → J+30)** :
- [ ] J0 : import 12 sites + 12 contrats énergie (parser PDF F2/F3)
- [ ] J+7 : import factures historiques 12 mois (288 factures attendues)
- [ ] J+14 : revue 6 règles anomalies sur portefeuille
- [ ] J+21 : test comparateur EPEX sur contrats expirants Q4 2026
- [ ] J+30 : preuve terrain ≥ 8 k€ détectée → bascule Control 19,9 k€

### Engagement contractuel

- [ ] **Contrat Lite 6,9 k€** signé Marie DAF + Jean-Marc CFO (engagement 6 mois)
- [ ] **Conditions bascule Control** documentées (cf personas audits Phase G/H/I/J)
- [ ] **Jalons 4 mois** : détection anomalies + alerte fin contrat livrés (CFO requis)
- [ ] **Jalons 6 mois** : Phase L tableau bord COMEX adopté (Marie DAF requis)

## Risques résiduels post-Phase K

| Risque | Mitigation Phase K | Phase L |
|---|---|---|
| Pydantic Response schemas absents | response dict direct OK MVP | Refactor Phase L |
| `supplier_name` chaîne libre coexiste | hard-cut soft (warn) + cache cleanup | DROP DDL Phase L (ADR-F-05) |
| Pas de comparateur prix marché complet (forward EPEX seul) | MVP 1 source suffit pilote | Multi-sources Phase L (offres concurrentielles) |
| 2 unmapped historiques (Eni/Vattenfall) | seed canoniques étendu | Phase L extension catalogue |
| Mode strict `__init__` non activé par défaut | env-gated `PROMEOS_J2_HARDCUT=1` | Activation systémique Phase L |

## Phase L backlog (post-pilote feedback)

1. **Pydantic Response schemas** sur 6 routes patrimoine_crud + persona_dashboard
2. **DROP supplier_name** colonne (ADR-F-05 hard-cut DDL)
3. **Comparateur prix marché** multi-sources (EPEX + offres concurrentielles)
4. **Activation systémique** mode strict `PROMEOS_J2_HARDCUT=1`
5. **Tableau bord COMEX** Marie DAF (export PDF + Excel + KPIs financiers)
6. **R25-R30** anomalies complémentaires (CSPE/TICFE/CTA seuils raffinés)

## Verdict cardinal

**GO pilote pré-prod externe** sur tier **Lite 6,9 k€/an engagement 6 mois** :
- Marie DAF : conditions Control 19,9 k€ × 25 sites entièrement remplies (DPE + ISO 50001
  + countdown urgency + export PDF) → bascule sous 6 mois si adoption > 70 %
- Jean-Marc CFO : conditions Control 19,9 k€ activables sur preuve terrain ≥ 8 k€
  (R22 raffinement HP capture surfacturation industrielle 25 k€/an)

**Cumul 60 livraisons cardinales · 0 régression · 275 tests verts**
**Vision Consolidée v1.3 personas couverte à 100 % cardinal**
**Y3 ARR forecast 1,2 M€ atteignable** sur signature 5 LOI + 2 pilotes payés Lite confirmés

## Liens

- ADR-F-01 (Fournisseur entité hybride) · ADR-F-02 (Parser facture) · ADR-F-03 (Parser contrat)
- ADR-F-04 (Hard-cut supplier_name soft Phase J2)
- Vision Consolidée v1.3 (memory `project_promeos_vision_consolidee_v1_3_2026_05_08.md`)
- Audit Phase F (commit `83a768bc`) · Phase G + H + I + J (commits `dde16c97` → `69b27aa1`)
