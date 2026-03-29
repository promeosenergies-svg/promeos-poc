# FEAT: Usage Knowledge Base — Exploitation Complète

**Date**: 2026-03-29
**Priorité**: P0
**Branche**: `feat/usage-knowledge-base`
**Dépendances**: patrimoine DIAMANT, KB, diagnostic conso, bill intelligence, cockpit

---

## 1. OBJECTIF

Faire des **usages énergétiques** le fil conducteur intelligent de PROMEOS.
Dès l'onboarding (création patrimoine), le système :
1. Détecte l'archétype du site via son code NAF (732 codes → 15 archétypes)
2. Contextualise automatiquement TOUTES les briques (diagnostic, anomalies, benchmarks, actions, trajectoire DT, billing)
3. Affiche le profil d'usage attendu vs. réel comme premier insight

**Règle d'or** : zéro configuration manuelle. NAF → tout le reste est automatique.

---

## 2. FICHIERS SOURCE (déjà générés, à commiter)

```
docs/base_documentaire/naf_archetype_mapping/
├── naf_to_archetype_v1.json          # 732 NAF → 15 archétypes (mapping complet)
├── archetypes_energy_v1.json         # 15 archétypes avec profils complets
└── manifest.json                     # Métadonnées, SHA256, provenance
```

---

## 3. PHASE 1 — SEED KB (backend)

### 3.1 Script de seed idempotent

**Fichier**: `backend/scripts/seed_kb_usages_v2.py`

```python
"""
Seed KB tables from naf_to_archetype_v1.json + archetypes_energy_v1.json.
Idempotent: keyed on `code`, upsert via merge.
"""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.kb_models import KBArchetype, KBMappingCode, KBAnomalyRule, KBRecommendation, KBVersion
from app.database import get_db_session

ARCHETYPES_PATH = Path("docs/base_documentaire/naf_archetype_mapping/archetypes_energy_v1.json")
MAPPING_PATH = Path("docs/base_documentaire/naf_archetype_mapping/naf_to_archetype_v1.json")

def seed_archetypes(db: Session):
    data = json.loads(ARCHETYPES_PATH.read_text())
    version = _ensure_kb_version(db, "USAGES_V2", "2026-03-29")

    for arch in data["archetypes"]:
        existing = db.query(KBArchetype).filter_by(code=arch["code"]).first()
        if existing:
            # UPDATE
            existing.title = arch["title"]
            existing.description = arch["description"]
            existing.kwh_m2_min = arch["kwh_m2_min"]
            existing.kwh_m2_max = arch["kwh_m2_max"]
            existing.kwh_m2_avg = arch["kwh_m2_avg"]
            existing.usage_breakdown_json = arch["usage_breakdown"]
            existing.temporal_signature_json = arch["temporal_signature"]
            existing.segment_tags = arch.get("naf_sections", [])
            existing.kb_version_id = version.id
        else:
            db.add(KBArchetype(
                code=arch["code"],
                title=arch["title"],
                description=arch["description"],
                kwh_m2_min=arch["kwh_m2_min"],
                kwh_m2_max=arch["kwh_m2_max"],
                kwh_m2_avg=arch["kwh_m2_avg"],
                usage_breakdown_json=arch["usage_breakdown"],
                temporal_signature_json=arch["temporal_signature"],
                segment_tags=arch.get("naf_sections", []),
                kb_version_id=version.id,
                source_section="archetypes_energy_v1",
                confidence="HIGH",
                status="VALIDATED"
            ))
    db.flush()

def seed_naf_mappings(db: Session):
    data = json.loads(MAPPING_PATH.read_text())
    version = _ensure_kb_version(db, "USAGES_V2", "2026-03-29")

    for m in data["mappings"]:
        archetype = db.query(KBArchetype).filter_by(code=m["archetype_code"]).first()
        if not archetype:
            continue
        existing = db.query(KBMappingCode).filter_by(naf_code=m["naf_code"]).first()
        if existing:
            existing.archetype_id = archetype.id
            existing.confidence = m["confidence"]
        else:
            db.add(KBMappingCode(
                naf_code=m["naf_code"],
                archetype_id=archetype.id,
                confidence=m["confidence"],
                priority=1,
                kb_version_id=version.id
            ))
    db.flush()

def seed_anomaly_rules(db: Session):
    """Seed 6 tier-1 rules with per-archetype thresholds."""
    data = json.loads(ARCHETYPES_PATH.read_text())
    version = _ensure_kb_version(db, "USAGES_V2", "2026-03-29")

    rules_def = [
        ("ANOM_BASE_NUIT_ELEVEE", "Base de nuit anormale", "base_nuit", "MEDIUM",
         "Ratio consommation nuit/jour supérieur au seuil sectoriel"),
        ("ANOM_WEEKEND_ELEVE", "Consommation weekend anormale", "weekend", "MEDIUM",
         "Ratio consommation weekend/semaine supérieur au seuil sectoriel"),
        ("ANOM_PUISSANCE_POINTE", "Puissance de pointe anormale", "puissance", "HIGH",
         "P_max > 95% P_souscrite OU P_max < 30% P_souscrite"),
        ("ANOM_PAS_SAISONNALITE", "Absence de saisonnalité", "saisonnalite", "HIGH",
         "CV mensuel < seuil — pas de variation chauffage/clim détectée"),
        ("ANOM_RATIO_M2_ANORMAL", "Ratio kWh/m² hors norme", "ratio_m2", "MEDIUM",
         "Intensité énergétique hors percentile P10-P90 sectoriel"),
        ("ANOM_GAZ_ETE", "Consommation gaz en été", "gaz_ete", "HIGH",
         "Gaz juin-août > seuil % de la conso annuelle gaz"),
    ]

    for code, title, rule_type, severity, desc in rules_def:
        thresholds = {}
        archetype_codes = []
        for arch in data["archetypes"]:
            key = code
            if key in arch.get("anomaly_thresholds", {}):
                thresholds[arch["code"]] = arch["anomaly_thresholds"][key]
                archetype_codes.append(arch["code"])

        existing = db.query(KBAnomalyRule).filter_by(code=code).first()
        if existing:
            existing.thresholds_json = thresholds
            existing.archetype_codes = archetype_codes
        else:
            db.add(KBAnomalyRule(
                code=code, title=title, description=desc,
                rule_type=rule_type, severity=severity,
                thresholds_json=thresholds,
                archetype_codes=archetype_codes,
                kb_version_id=version.id,
                confidence="HIGH", status="VALIDATED"
            ))
    db.flush()

def _ensure_kb_version(db: Session, name: str, date: str) -> KBVersion:
    existing = db.query(KBVersion).filter_by(name=name).first()
    if existing:
        return existing
    v = KBVersion(name=name, description=f"Usage KB v2 — {date}", status="ACTIVE")
    db.add(v)
    db.flush()
    return v

def run_seed():
    db = next(get_db_session())
    try:
        seed_archetypes(db)
        seed_naf_mappings(db)
        seed_anomaly_rules(db)
        db.commit()
        n_arch = db.query(KBArchetype).count()
        n_map = db.query(KBMappingCode).count()
        n_rules = db.query(KBAnomalyRule).count()
        print(f"✓ Seed OK: {n_arch} archetypes, {n_map} NAF mappings, {n_rules} rules")
        assert n_arch == 15, f"Expected 15 archetypes, got {n_arch}"
        assert n_map == 732, f"Expected 732 mappings, got {n_map}"
        assert n_rules >= 6, f"Expected ≥6 rules, got {n_rules}"
    except Exception as e:
        db.rollback()
        print(f"✗ Seed FAILED: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
```

---

## 4. PHASE 2 — AUTO-AFFECTATION ARCHÉTYPE (backend)

### 4.1 Schema change sur `Site`

**Fichier**: `backend/models/site.py` — ajouter 3 colonnes :

```python
archetype_id = Column(Integer, ForeignKey('kb_archetype.id'), nullable=True, index=True)
archetype_confidence = Column(String(10), nullable=True)  # HIGH/MEDIUM/LOW
archetype_source = Column(String(20), nullable=True)       # naf_mapping | signature_match | manual
```

### 4.2 Service d'auto-affectation

**Fichier**: `backend/services/usage_profiling_service.py`

```python
class UsageProfilingService:
    """Service central pour le profilage énergétique des sites."""

    def assign_archetype_from_naf(self, site_id: int, db: Session) -> dict | None:
        """
        NAF → archétype via kb_mapping_code.
        Cascade de résolution : site.naf_code → entite.naf_code → None.
        """
        site = db.query(Site).get(site_id)
        if not site:
            return None

        naf = site.naf_code
        if not naf and site.portefeuille:
            entite = site.portefeuille.entite_juridique
            if entite:
                naf = entite.naf_code

        if not naf:
            return None

        naf = self._normalize_naf(naf)

        mapping = (db.query(KBMappingCode)
                   .filter_by(naf_code=naf)
                   .order_by(KBMappingCode.priority)
                   .first())

        if not mapping:
            return None

        site.archetype_id = mapping.archetype_id
        site.archetype_confidence = mapping.confidence
        site.archetype_source = 'naf_mapping'
        db.flush()

        archetype = db.query(KBArchetype).get(mapping.archetype_id)
        return {
            "site_id": site_id,
            "archetype_code": archetype.code,
            "archetype_title": archetype.title,
            "confidence": mapping.confidence,
            "source": "naf_mapping",
            "naf_code": naf
        }

    def assign_archetypes_bulk(self, org_id: int, db: Session) -> dict:
        """Assign archetypes to all sites without one in an org."""
        sites = (db.query(Site)
                 .join(Site.portefeuille)
                 .join(Portefeuille.entite_juridique)
                 .filter(EntiteJuridique.organisation_id == org_id)
                 .filter(Site.archetype_id.is_(None))
                 .all())
        results = {"assigned": 0, "skipped": 0, "errors": 0}
        for site in sites:
            try:
                r = self.assign_archetype_from_naf(site.id, db)
                if r:
                    results["assigned"] += 1
                else:
                    results["skipped"] += 1
            except Exception:
                results["errors"] += 1
        db.commit()
        return results

    def get_usage_profile(self, site_id: int, db: Session) -> dict:
        """Retourne le profil d'usage complet d'un site."""
        site = db.query(Site).get(site_id)
        if not site:
            return None

        archetype = db.query(KBArchetype).get(site.archetype_id) if site.archetype_id else None

        actual_kwh_m2 = None
        benchmark_position = None
        if site.surface_m2 and site.surface_m2 > 0:
            annual_kwh = self._get_annual_consumption(site_id, db)
            if annual_kwh:
                actual_kwh_m2 = round(annual_kwh / site.surface_m2, 1)
                if archetype:
                    benchmark_position = self._compute_percentile(
                        actual_kwh_m2, archetype.kwh_m2_min, archetype.kwh_m2_max
                    )

        applicable_rules = []
        if archetype:
            rules = (db.query(KBAnomalyRule)
                     .filter(KBAnomalyRule.status == 'VALIDATED')
                     .all())
            for rule in rules:
                codes = rule.archetype_codes or []
                if archetype.code in codes or not codes:
                    applicable_rules.append({
                        "code": rule.code,
                        "title": rule.title,
                        "severity": rule.severity,
                        "threshold": (rule.thresholds_json or {}).get(archetype.code)
                    })

        return {
            "site_id": site_id,
            "site_name": site.nom,
            "archetype": {
                "code": archetype.code if archetype else None,
                "title": archetype.title if archetype else "Non déterminé",
                "kwh_m2_range": [archetype.kwh_m2_min, archetype.kwh_m2_max] if archetype else None,
                "kwh_m2_avg": archetype.kwh_m2_avg if archetype else None,
                "source": site.archetype_source,
                "confidence": site.archetype_confidence
            },
            "expected_breakdown": archetype.usage_breakdown_json if archetype else None,
            "temporal_signature": archetype.temporal_signature_json if archetype else None,
            "actual_kwh_m2": actual_kwh_m2,
            "benchmark_position": benchmark_position,
            "anomaly_rules_applicable": applicable_rules
        }

    def _normalize_naf(self, naf: str) -> str:
        """7010Z → 70.10Z, 70.10 → 70.10Z"""
        naf = naf.strip().replace(' ', '')
        if len(naf) == 5 and '.' not in naf:
            naf = naf[:2] + '.' + naf[2:]
        if len(naf) == 5 and naf[-1].isdigit():
            naf += 'Z'
        return naf

    def _compute_percentile(self, value, p10, p90):
        if p90 == p10:
            return "P50"
        pct = int(10 + (value - p10) / (p90 - p10) * 80)
        pct = max(1, min(99, pct))
        return f"P{pct}"

    def _get_annual_consumption(self, site_id, db):
        from app.services.consumption_unified_service import get_site_annual_kwh
        return get_site_annual_kwh(site_id, db)
```

### 4.3 Endpoints API

**Fichier**: `backend/routes/usage_profile.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/usage-profile", tags=["usage-profile"])

@router.get("/sites/{site_id}")
def get_site_usage_profile(site_id: int, db: Session = Depends(get_db)):
    """Profil d'usage complet d'un site (archétype, breakdown, benchmark, règles)."""
    service = UsageProfilingService()
    profile = service.get_usage_profile(site_id, db)
    if not profile:
        raise HTTPException(404, "Site not found")
    return profile

@router.post("/sites/{site_id}/assign-archetype")
def assign_site_archetype(site_id: int, db: Session = Depends(get_db)):
    """Force l'affectation archétype depuis NAF."""
    service = UsageProfilingService()
    result = service.assign_archetype_from_naf(site_id, db)
    if not result:
        raise HTTPException(422, "No NAF code found or no matching archetype")
    db.commit()
    return result

@router.post("/org/{org_id}/assign-archetypes-bulk")
def assign_org_archetypes_bulk(org_id: int, db: Session = Depends(get_db)):
    """Affectation bulk pour toute une organisation."""
    service = UsageProfilingService()
    return service.assign_archetypes_bulk(org_id, db)

@router.get("/archetypes")
def list_archetypes(db: Session = Depends(get_db)):
    """Liste des 15 archétypes disponibles."""
    archetypes = db.query(KBArchetype).filter_by(status='VALIDATED').all()
    return [{"code": a.code, "title": a.title, "kwh_m2_avg": a.kwh_m2_avg} for a in archetypes]

@router.get("/naf/{naf_code}")
def lookup_naf(naf_code: str, db: Session = Depends(get_db)):
    """Lookup NAF → archétype (pour l'onboarding)."""
    service = UsageProfilingService()
    naf = service._normalize_naf(naf_code)
    mapping = db.query(KBMappingCode).filter_by(naf_code=naf).first()
    if not mapping:
        return {"naf_code": naf, "archetype": None, "message": "Code NAF non reconnu"}
    arch = db.query(KBArchetype).get(mapping.archetype_id)
    return {
        "naf_code": naf,
        "archetype_code": arch.code,
        "archetype_title": arch.title,
        "confidence": mapping.confidence,
        "kwh_m2_range": [arch.kwh_m2_min, arch.kwh_m2_max],
        "usage_breakdown": arch.usage_breakdown_json
    }
```

---

## 5. PHASE 3 — HOOKS PATRIMOINE (intégration onboarding)

### 5.1 Hook sur création/activation de site

**Fichier**: `backend/services/patrimoine_service.py` — dans `activate_site()` et `create_site()` :

```python
# Après la création/activation du site :
from app.services.usage_profiling_service import UsageProfilingService

profiling = UsageProfilingService()
result = profiling.assign_archetype_from_naf(site.id, db)
if result:
    logger.info(f"Site {site.id} auto-profiled: {result['archetype_code']} ({result['confidence']})")
```

### 5.2 Hook Intake Wizard

**Fichier**: `frontend/src/pages/IntakeWizard.jsx` — step "Activité / NAF"

Quand l'utilisateur saisit ou sélectionne un NAF :
```javascript
const { data: nafProfile } = useQuery(
  ['naf-lookup', nafCode],
  () => api.get(`/api/usage-profile/naf/${nafCode}`),
  { enabled: nafCode?.length >= 5 }
);
```

### 5.3 Seed HELIOS mise à jour

| Site | NAF actuel | Archétype attendu |
|------|-----------|-------------------|
| Paris Bureaux 3500m² | 70.10Z | BUREAU_STANDARD |
| Lyon Bureaux 1200m² | 69.10Z | BUREAU_STANDARD |
| Marseille École 2800m² | 85.31Z | ENSEIGNEMENT |
| Nice Hôtel 4000m² | 55.10Z | HOTEL_HEBERGEMENT |
| Toulouse Entrepôt 6000m² | 52.10B | LOGISTIQUE_SEC |

---

## 6. PHASE 4 — EXPLOITATION TRANSVERSALE (toutes briques)

### 6.1 Diagnostic Conso — seuils KB-driven

Remplacer tout seuil hardcodé par lookup `KBAnomalyRule.thresholds_json[archetype_code]`.

### 6.2 Cockpit — KPI contextualisé

- Vue Exploitation : badge archétype pour chaque site
- Vue COMEX : répartition portefeuille par archétype (pie chart)
- Benchmark : "Votre bureau Paris consomme 196 kWh/m² — P62 du benchmark bureaux (médiane: 180)"

### 6.3 Bill Intelligence — estimation shadow billing contextualisée

L'archétype informe la plausibilité d'une facture.

### 6.4 Centre d'Action — recommandations contextualisées

Anomalie ANOM_BASE_NUIT sur bureau → reco "Prises coupe-veille IT, programmation CVC nuit"
Anomalie ANOM_BASE_NUIT sur commerce alimentaire → PAS d'alerte (froid 24/7 normal, seuil 0.75)

### 6.5 Conformité DT — modulation par usage

Changement d'activité détecté (archétype NAF ≠ archétype signature conso) = signal modulation DT.

### 6.6 Portfolio — benchmark inter-sites par archétype

Même archétype = sites comparables.

---

## 7. TESTS

```python
# test_seed_kb_usages_v2.py
def test_seed_creates_15_archetypes()
def test_seed_creates_732_mappings()
def test_seed_creates_6_anomaly_rules()
def test_seed_idempotent()

# test_usage_profiling_service.py
def test_naf_7010Z_maps_to_bureau_standard()
def test_naf_5510Z_maps_to_hotel_hebergement()
def test_naf_4711D_maps_to_commerce_alimentaire()
def test_naf_8531Z_maps_to_enseignement()
def test_naf_5210A_maps_to_logistique_froid()
def test_naf_5210B_maps_to_logistique_sec()
def test_naf_6311Z_maps_to_data_center()
def test_naf_unknown_returns_none()
def test_naf_normalize_7010Z()
def test_naf_normalize_7010()
def test_cascade_entite_naf_if_site_naf_missing()
def test_bulk_assign_org()

# test_usage_profile_endpoint.py
def test_get_profile_returns_archetype()
def test_get_profile_returns_breakdown()
def test_get_profile_returns_benchmark_position()
def test_get_profile_returns_applicable_rules()
def test_naf_lookup_returns_archetype()

# test_contextual_thresholds.py
def test_bureau_nuit_threshold_020()
def test_commerce_alim_nuit_threshold_075()
def test_hotel_nuit_threshold_065()
def test_data_center_nuit_threshold_098()
def test_enseignement_weekend_threshold_020()

# test_helios_archetypes.py
def test_paris_bureau_standard()
def test_marseille_enseignement()
def test_nice_hotel()
def test_toulouse_logistique_sec()
```

---

## 8. DEFINITION OF DONE

1. `seed_kb_usages_v2.py` → 15 archétypes, 732 NAF mappings, 6 rules — idempotent
2. Création site avec NAF → archétype auto-assigné, visible dans snapshot
3. `GET /api/usage-profile/sites/{id}` → réponse complète
4. `GET /api/usage-profile/naf/{code}` → lookup instantané
5. Intake Wizard affiche le profil détecté en temps réel
6. Diagnostic Conso utilise seuils KB par archétype
7. Seed HELIOS : 5 sites avec archétypes cohérents
8. Tous tests green, zéro régression sur 280+ backend + 5664+ frontend
9. Fichiers JSON commités dans `docs/base_documentaire/naf_archetype_mapping/`

---

## 9. EXPLOITATION PRODUIT — FLUX COMPLET

```
ONBOARDING                    MONITORING                     ACTIONS
─────────                     ──────────                     ───────
SIRET saisi                   Données conso reçues           Anomalie détectée
    │                              │                              │
    ▼                              ▼                              ▼
NAF extrait (API Sirene)      Features calculées              Règle KB consultée
    │                         (nuit/jour, WE, CV,             (seuil par archétype)
    ▼                          kWh/m², facteur charge)             │
kb_mapping_code lookup             │                              ▼
    │                              ▼                          Reco KB matchée
    ▼                         Comparaison vs archétype        (ICE scoring)
Archétype assigné             signature attendue                   │
    │                              │                              ▼
    ▼                              ▼                          ActionItem créée
Usage profile créé            Anomalies contextualisées       (priorité = ICE)
    │                         (seuils adaptés)                     │
    ├── Cockpit (badge)            │                              ▼
    ├── Portfolio (benchmark)      ├── Alerte contextualisée  Centre d'Action
    ├── Billing (plausibilité)     ├── Insight Conso          (filtré par archétype)
    └── DT (référence usage)      └── Score santé site
```
