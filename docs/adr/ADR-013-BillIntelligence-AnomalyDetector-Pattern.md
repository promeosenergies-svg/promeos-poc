# ADR-013 — Bill Intelligence anomaly_detector pattern (R19 + R20)

**Statut** : Accepté
**Date** : 2026-05-05
**Sprint** : C-5 Phase 0 (build Phase 5.1)
**Personnes impliquées** : Amine (founder), Claude architect-helios + bill-intelligence + regulatory-expert
**Tracking dette** : `D-Phase4-2d-BillIntelligence-Anomaly-Detector-001` (P0 Sprint C-4 Phase 4.2d) → CLÔTURÉE Phase 5.1

---

## Contexte

L'audit multi-agents Sprint C-4 Phase 4.2d (commit `d131205d`) a détecté que le **différenciateur Bill Intelligence** annoncé en KB stratégique (`project_strategic_priorities_2026_avril.md`, `feedback_simple_differenciant.md`) **n'a aucun runtime opérationnel** :

- **R19 (VNU dormant)** — détection ligne facture > 0 EUR pour VNU alors que prix marché < seuil 1 (78 EUR/MWh) = facturation erronée fournisseur
- **R20 (capacité variance >5%)** — détection variance > 5% entre puissance souscrite contractuelle et puissance facturée = cas embrouille TURPE

### Audit Phase 0 Sprint C-5 — diagnostic terrain T0

- `backend/services/bill_intelligence/` **n'existe pas** (module à créer from scratch)
- VNU dormant logic **partielle** : `services/purchase/cost_simulator_2026.py` mentionne le statut informatif ("dormant/actif selon seuil CRE") mais **n'effectue aucune détection runtime sur factures réelles**
- `services/demo_seed/orchestrator.py:1268-1269` : seed 2 KB articles VNU pédagogiques (cadre 2026+ post-ARENH) — pas de détection
- **Aucune détection anomalies billing existante** dans `routes/billing/*` ni `services/billing_engine/*`
- Modèles existants : `Facture` (header), `LigneFacture` (détail), `BillingComponent` (composante facturée). Aucun modèle `BillAnomaly` ni `BillingAlert`.
- **Dette clé connue** : seuils CRE versionnés via `config/sources_reglementaires.yaml` (Sprint C-3 Phase 3.2) — pas de redondance autorisée
- **CFO scrute anomalies** : interview persona Marie DAF tertiaire (KB `feedback_simple_differenciant.md`) confirme que "anomalie facture détectée + correctif chiffré" = top 3 de ses pain points B2B mid-market

### Compétiteurs sans Bill Intelligence dédié

- **Deepki** : conformité décret tertiaire + benchmark, pas d'anomaly detection facture
- **Spacewell** : IWMS + EMS, pas de détection R19/R20
- **HelloWatt** : B2C résidentiel principalement, anomalies basiques
- **Metron** : EMS industriel, pas de billing intelligence
- **Selectra** : courtage, pas d'anomaly post-souscription

→ Différenciateur cardinal PROMEOS = **détection R19/R20/Rxx documentée + traçable + chiffrée** (économie potentielle EUR par anomalie).

---

## Décision

### Option retenue : **Rules-based pure + seuils YAML SoT + modèle BillAnomaly nouveau + trigger ingestion**

3 décisions cardinales :

#### 1. Architecture détection — rules-based pure (pas ML hybride MVP)

```python
# backend/services/bill_intelligence/anomaly_detector.py (nouveau)
def detect_r19_vnu_dormant(facture: Facture, db: Session) -> list[BillAnomaly]:
    """R19 : VNU facturé > 0 EUR alors que prix marché < seuil 1 CRE."""
    ...

def detect_r20_capacity_variance(facture: Facture, db: Session) -> list[BillAnomaly]:
    """R20 : variance > 5% entre puissance souscrite contractuelle et puissance facturée."""
    ...

def run_all_detectors(facture: Facture, db: Session) -> list[BillAnomaly]:
    """Pipeline détection : R19 + R20 + Rxx futurs (open-closed principle)."""
    detectors = [detect_r19_vnu_dormant, detect_r20_capacity_variance]
    return [a for d in detectors for a in d(facture, db)]
```

**Justification rules-based MVP** :

- Seuils CRE strictement définis (pas de zone grise) → pas besoin ML
- Auditabilité légale (CFO peut justifier "voici la règle violée + référence CRE")
- Vélocité Sprint C-5 (~2-3 j-h vs ~5-7 j-h ML hybride pipeline)
- ML hybride reporté Sprint C-7+ si patterns complexes émergent (ex: R21 anomalies CTA, R22 saisonnalité)

#### 2. Seuils paramétrables — YAML SoT cohérent Sprint C-3

Ajout `backend/config/sources_reglementaires.yaml` (extension Phase 3.2) :

```yaml
BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR:
  value: 0.01  # toute somme > 0 = anomalie (VNU dormant = pas facturable)
  unit: EUR
  effective_date: "2026-01-01"
  legal_reference: "CRE délibération 2024-XX (post-ARENH 31/12/2025)"
  source: "config/sources_reglementaires.yaml + audit Phase 0 Sprint C-5"
  notes: "VNU = Versement Nucléaire Universel ; dormant si prix marché < seuil 1 (78 EUR/MWh)"
  status: "active"
  confidence: "high"

BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT:
  value: 5.0
  unit: "%"
  effective_date: "2026-01-01"
  legal_reference: "Pratique courante audit TURPE 7 (HTA/BT) — variance > 5% = revoir contrat"
  source: "config/sources_reglementaires.yaml + audit Phase 0 Sprint C-5"
  notes: "Variance = abs(puissance_souscrite - puissance_facturée_max) / puissance_souscrite × 100"
  status: "active"
  confidence: "high"
```

**Justification YAML SoT** :

- Cohérence Sprint C-3 (`regulatory_sources_loader.py` pattern @lru_cache) — pas de duplication code
- Versionning légal (CRE peut évoluer seuil) sans redéploiement
- TraceTooltip frontend (R10 différenciateur Sprint C-3) peut afficher "seuil VNU 0,01 EUR/MWh CRE délibération 2024-XX"
- Source-guards anti-drift YAML ↔ runtime (extension SG existant Sprint C-3)

#### 3. Modèle output — `BillAnomaly` nouveau (pas réutilisation `Anomaly` KB Phase 1-4)

```python
# backend/models/bill_anomaly.py (nouveau)
class BillAnomaly(Base, SoftDeleteMixin):
    __tablename__ = "bill_anomalies"

    id = Column(Integer, primary_key=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=False, index=True)
    code = Column(String(10), nullable=False)  # "R19", "R20", futur "R21"
    severity = Column(String(20), nullable=False, default="info")  # info / warning / critical
    description = Column(String(500), nullable=False)
    economic_impact_eur = Column(Float, nullable=True)  # économie potentielle si anomalie corrigée
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id = Column(Integer, nullable=True)  # traçabilité opérateur
    resolution_notes = Column(String(1000), nullable=True)

    # Snapshot données détection (audit trail)
    detection_inputs_json = Column(JSON, nullable=False)  # {"vnu_amount": 12.50, "market_price": 65.0, ...}
    detection_threshold_yaml_ref = Column(String(80), nullable=True)  # "BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR"

    # Index composite anti-N+1 query frontend
    __table_args__ = (
        Index("ix_bill_anomalies_facture_code", "facture_id", "code"),
    )
```

**Justification nouveau modèle (pas réutilisation `Anomaly` KB)** :

- Sémantique distincte : `Anomaly` KB Phase 1-4 = anomalies consommation (delta CDC, courbe atypique) ; `BillAnomaly` = anomalies **facturation** (erreurs fournisseur, surfacturation)
- Traçabilité audit légale différente : `BillAnomaly` doit tracer `detection_threshold_yaml_ref` (source légale CRE) ; `Anomaly` KB trace stat features
- Économie quantifiée (`economic_impact_eur`) = différenciateur produit visible CFO ; absent du modèle KB
- Migration future possible vers Anomaly unifié si patterns convergent (ADR-XXX Sprint C-7+)

#### 4. Intégration cascade — trigger ingestion immédiat + batch nightly fallback

- **Trigger ingestion** : appelé dans `routes/billing/factures.py:create_facture` post-validation, exécution synchrone (~50-200 ms)
- **Batch nightly fallback** : `services/cron/bill_anomaly_batch.py` (nouveau) re-scan 30 derniers jours pour rattrapage si trigger ingestion échoue (résilience)
- **CASCADE_MAP integration** : pas requis MVP (anomaly = output read-only, pas re-cascade vers autres entités)

#### 5. Endpoint REST — `/api/bill-intelligence/anomalies` org-scopé

```python
# backend/routes/bill_intelligence.py (nouveau)
@router.get("/anomalies")
def list_anomalies(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
    severity: Optional[str] = Query(None),
    code: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
):
    """Liste anomalies billing org-scopées (resolve_org_id obligatoire)."""
    org_id = resolve_org_id(request, auth, db)
    ...
```

**Justification endpoint dédié** :

- Org-scoping CARDINAL (ne pas exposer anomalies cross-tenant) — règle PROMEOS non-négociable #2
- Filtres pratiques CFO : par sévérité (critical first), par code (R19/R20), par statut (resolved/pending)
- Pas de couplage avec `routes/billing/factures.py` (séparation domain Bill Intelligence vs core billing)

---

## Conséquences

### Positives

- **Différenciateur produit cardinal opérationnel** — runtime R19+R20 détection traçable + chiffrée
- **Cohérence YAML SoT Sprint C-3** — pas de redondance constants, traçabilité légale via TraceTooltip R10
- **Auditabilité légale** — CFO peut justifier chaque anomalie via `detection_threshold_yaml_ref` + CRE délibération
- **Open-closed principle** — futurs détecteurs Rxx (R21 CTA, R22 saisonnalité) ajoutables sans toucher ingestion existante
- **Économie chiffrée** (`economic_impact_eur`) — argument commercial fort B2B mid-market

### Négatives

- **Nouveau modèle SQLAlchemy** + migration Alembic 8e propre (anti-DROP discipline 8e épisode)
- **Trigger ingestion synchrone** = +50-200 ms par création facture (acceptable seuil perf 2 sec validé Sprint C-4 Phase 4.6)
- **2 sources de vérité Anomaly cohabitent** (KB consommation + BillAnomaly facture) — peut créer confusion produit ; mitigation = nommage explicite frontend ("Anomalie consommation" vs "Anomalie facture")
- **Pas d'auto-correction proposée MVP** — détection seulement (correction = workflow utilisateur Sprint C-7+)

### Mitigation

- **Source-guards** : `tests/source_guards/test_bill_anomaly_yaml_constants_source_guards.py` cohérence YAML ↔ runtime
- **Tests fixtures HELIOS** : factures avec/sans R19/R20 préseedées (`services/demo_seed/gen_billing.py` extension)
- **Tests perf** : trigger ingestion < 200 ms sur 100 factures consécutives (`@pytest.mark.perf`)
- **Doc CFO** : `frontend/src/pages/bill-intelligence/AnomalyExplainer.jsx` (composant pédagogique TraceTooltip — Sprint C-7 polish)

---

## Implémentation Sprint C-5 Phase 5.1

### Composants livrés (estimé ~2-3 j-h, P0 cardinal)

1. **Modèle** `backend/models/bill_anomaly.py` (nouveau, ~80 LOC)
2. **Migration Alembic** `backend/alembic/versions/XXXX_bill_anomaly_table.py` (8e propre, anti-DROP discipline)
3. **YAML SoT** extension `backend/config/sources_reglementaires.yaml` (+2 termes BILL_ANOMALY_*)
4. **Service** `backend/services/bill_intelligence/anomaly_detector.py` (nouveau, ~150 LOC)
   - `detect_r19_vnu_dormant(facture, db) -> list[BillAnomaly]`
   - `detect_r20_capacity_variance(facture, db) -> list[BillAnomaly]`
   - `run_all_detectors(facture, db) -> list[BillAnomaly]`
5. **Trigger** `backend/routes/billing/factures.py:create_facture` ajout post-commit appel `run_all_detectors`
6. **Endpoint** `backend/routes/bill_intelligence.py` (nouveau, ~80 LOC) — `GET /api/bill-intelligence/anomalies`
7. **Tests** ~10-15 tests (unit detect_r19 / detect_r20 / endpoint org-scope / SG cohérence YAML)
8. **Source-guards** ~2 SG (YAML ↔ runtime + endpoint org-scoped)

### Livrables Phase 5.1 (estimation détaillée)

| Composant | Effort | Tests |
|---|---|---|
| Modèle + migration Alembic | ~30 min | +3 |
| YAML extension | ~15 min | +1 |
| Service anomaly_detector | ~1 h | +6 |
| Trigger ingestion | ~30 min | +2 |
| Endpoint REST | ~30 min | +3 |
| Source-guards | ~30 min | +2 |
| **Total** | **~2-3 h** | **+17** |

---

## Adaptations Phase 5.1.0 (post-diagnostic mini-audit)

3 adaptations cardinales détectées Étape 5.1.0 lors du diagnostic terrain :

1. **`BillAnomaly.invoice_id` FK `energy_invoices.id`** (pas `facture_id` FK `facture`) — modèle existant est `EnergyInvoice` (`backend/models/billing_models.py:319`), pas `Facture`.
2. **R19 scan `EnergyInvoiceLine`** : pas de champ direct `invoice.vnu_montant`. Détection via `line_type=tax` + label LIKE `%VNU%` (ou variantes "VERSEMENT NUCLEAIRE"/"VERSEMENT NUCLÉAIRE") + agrégation Σ `amount_eur`.
3. **R20 JSON dict navigation** : `PowerContract.ps_par_poste_kva` est dict JSON `{HPH: 36, HCH: 36, ...}` indexé par poste tarifaire (pas scalaire). R20 retourne LISTE d'anomalies (1 par poste). Matching `period_code` cardinal via helper `_resolve_period_code` (3 priorités : champ direct → `meta_json` → label parsing). JOIN chain : `EnergyInvoice → Site → Meter → PowerContract` (pas DeliveryPoint direct).

Sémantique ADR-013 préservée : rules-based pure + YAML SoT + `BillAnomaly` nouveau + trigger ingestion. Effort réel ~2 h vs ~2-3 h initial (adaptations bénignes).

### Livrables effectifs Phase 5.1 (commit Sprint C-5)

- **Migration Alembic 8e propre** (`478ee4a61ebb_phase_5_1_sprint_c_5_bill_anomaly_table_.py`) — 14 `drop_table` autogenerate retirés discipline anti-DROP 8e épisode (cumul Phase C : 0 destructive)
- **Modèle** `backend/models/bill_anomaly.py` (~80 LOC) avec 4 index (invoice_id, code+severity, detected_at, deleted_at)
- **Service** `backend/services/bill_intelligence/anomaly_detector.py` (~280 LOC, vs 150 LOC initial — +adaptations)
- **YAML SoT** : 2 termes ajoutés domain `bill_intelligence`
- **Endpoint** `routes/bill_intelligence.py` (~95 LOC) — `GET /api/bill-intelligence/anomalies` org-scopé strict
- **Tests** 19/19 verts (R19 5 + R20 7 + helper 3 + pipeline 2 + YAML 2)
- **Source-guards** 3/3 verts (YAML termes + no-hardcode + helper signature)

---

## Références

- Tracking dette : `docs/audits/DETTE_TECHNIQUE_TRACKER.md` (`D-Phase4-2d-BillIntelligence-Anomaly-Detector-001`)
- Bilan Sprint C-4 : `docs/audits/BILAN_SPRINT_C4_2026_05_05.md` (Phase 4.2d audit multi-agents)
- Sprint C-3 YAML SoT pattern : ADR-008 + `config/sources_reglementaires.yaml`
- Memory KB : `feedback_simple_differenciant.md`, `project_strategic_priorities_2026_avril.md`, `reference_methodologie_elec_shadow_billing.md`
- VNU contexte : `services/demo_seed/orchestrator.py:1268-1269`
