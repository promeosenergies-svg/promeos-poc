# ADR-024 — Moteur d'assujettissement réglementaire

**Status** : `Accepted` (acté Phase 3.5 livraison 13/05/2026 — 5 évaluateurs implémentés et catalogués, audit regulatory-expert verdict RÉSERVES avec 2 fixes immédiats appliqués : BEGES périodicité 4→3 + APER.TOITURE deadline)
**Date** : 2026-05-13
**Author** : Amine + Claude (session refonte Synthèse v6→v8)
**Supersedes** : —
**Related** : ADR-023 (Synthèse stratégique data-driven), ADR-020 (OPERAT scoring), ADR-022 (priorisation v1.0)

---

## Context

La page **Synthèse stratégique** ne peut pas afficher une trajectoire DT 2030 si le patrimoine **n'est pas assujetti** au décret tertiaire. Elle ne peut pas exiger l'audit SMÉ si l'entreprise est PME. Elle ne peut pas chiffrer un retrofit BACS si aucun bâtiment n'a un système thermique > 70 kW.

Aujourd'hui, ces vérifications sont **dispersées** (services compliance, scoring, billing, frontend feature flags). Conséquence :

1. **Risque de divergence** : un site `is_demo=True` peut être affiché comme assujetti DT alors que la fixture n'a pas la SDP requise
2. **Pas de traçabilité** : aucun moyen d'expliquer à l'utilisateur "pourquoi cette règle s'applique à ce site"
3. **Pas de versioning** : si le décret BACS bascule de 290 kW à 70 kW (échéance 2030), aucune piste d'audit
4. **Frontend en aveugle** : la page Cockpit/Synthèse doit deviner si elle peut afficher la trajectoire DT

Cette ADR définit le **moteur d'assujettissement** unique : un service backend qui répond à la question "**ce site/portefeuille est-il assujetti à cette règle, et pourquoi ?**" avec preuve textuelle, statut versionné et confiance.

---

## Decision

### 1. Modèle de données — Statut d'applicabilité

```python
# backend/regulatory/applicability_types.py

from enum import StrEnum
from dataclasses import dataclass
from datetime import date

class ApplicabilityStatus(StrEnum):
    APPLICABLE     = "applicable"      # règle s'applique → action ou trajectoire visible
    NOT_APPLICABLE = "not_applicable"  # règle ne s'applique pas → masquée ou grisée
    UNKNOWN        = "unknown"         # statut indéterminable → bandeau "à clarifier"
    DATA_MISSING   = "data_missing"    # champs patrimoine manquants → CTA "renseigner"

class RuleCode(StrEnum):
    DT     = "DT"      # Décret tertiaire 2019-771
    BACS   = "BACS"    # Décret BACS 2020-887
    APER   = "APER"    # Loi APER 2023-175 (parkings 1500 m² + ombrières)
    SME    = "SME"     # Audit SMÉ obligatoire (250+ salariés OU 50M€ CA + bilan 43M€)
    BEGES  = "BEGES"   # Bilan GES réglementaire (500+ salariés métropole / 250+ DOM)

@dataclass(frozen=True)
class RuleApplicability:
    rule:           RuleCode
    site_id:        int | None              # None = portée portefeuille/organisation
    status:         ApplicabilityStatus
    reason_human:   str                      # phrase complète, prête à afficher
    reason_code:    str                      # ex. "DT.SDP_LT_1000", "BACS.NO_SYSTEM_GT_70KW"
    confidence:     float                    # 0.0..1.0
    missing_fields: list[str]                # si DATA_MISSING : liste champs à renseigner
    evidence:       dict                      # données ayant servi à conclure (SDP, NAF, etc.)
    rule_version:   str                      # "DT-2019-771-v2024-10-01"
    computed_at:    str                      # ISO datetime
```

### 2. Service unique — `regulatory_applicability_service`

```python
# backend/services/regulatory_applicability_service.py

def compute_applicability(
    db: Session,
    org_id: int,
    site_ids: list[int] | None = None,
) -> dict[RuleCode, list[RuleApplicability]]:
    """
    Évalue l'applicabilité de toutes les règles cataloguées pour une organisation.

    Retourne un dict { "DT": [RuleApplicability, ...], "BACS": [...], ... }
    Une entrée par site quand la règle est site-scoped (DT, BACS, APER),
    une entrée unique avec site_id=None pour les règles org-scoped (SMÉ, BEGES).
    """
    sites = _load_sites(db, org_id, site_ids)
    org   = _load_org(db, org_id)
    result: dict[RuleCode, list[RuleApplicability]] = {r: [] for r in RuleCode}

    for rule in RuleCode:
        evaluator = RULE_EVALUATORS[rule]
        if evaluator.scope == "site":
            for site in sites:
                result[rule].append(evaluator.evaluate_site(db, site))
        else:
            result[rule].append(evaluator.evaluate_org(db, org, sites))

    return result
```

### 3. Évaluateurs par règle — pattern standard

```python
# backend/regulatory/rules/dt.py

class DTEvaluator(RuleEvaluator):
    code = RuleCode.DT
    scope = "site"
    version = "DT-2019-771-v2024-10-01"

    def evaluate_site(self, db, site) -> RuleApplicability:
        # 1. Vérifier champs requis présents
        missing = []
        if site.sdp_m2 is None:        missing.append("site.sdp_m2")
        if site.usage_principal is None: missing.append("site.usage_principal")
        if missing:
            return self._data_missing(site, missing)

        # 2. Règle : SDP >= 1000 m² ET usage tertiaire
        if site.sdp_m2 < 1000:
            return RuleApplicability(
                rule=RuleCode.DT, site_id=site.id,
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason_human=f"Site {site.name} : SDP {site.sdp_m2} m² < 1 000 m². Décret tertiaire non applicable.",
                reason_code="DT.SDP_LT_1000",
                confidence=1.0,
                missing_fields=[],
                evidence={"sdp_m2": site.sdp_m2},
                rule_version=self.version,
                computed_at=_now_iso(),
            )

        if not _is_tertiary(site.usage_principal):
            return RuleApplicability(
                rule=RuleCode.DT, site_id=site.id,
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reason_human=f"Site {site.name} : usage {site.usage_principal} hors tertiaire. Décret tertiaire non applicable.",
                reason_code="DT.USAGE_NON_TERTIARY",
                confidence=1.0,
                missing_fields=[],
                evidence={"usage": site.usage_principal},
                rule_version=self.version,
                computed_at=_now_iso(),
            )

        return RuleApplicability(
            rule=RuleCode.DT, site_id=site.id,
            status=ApplicabilityStatus.APPLICABLE,
            reason_human=f"Site {site.name} : SDP {site.sdp_m2} m² ≥ 1 000 m², usage tertiaire. Trajectoire -40 %/2030, -50 %/2040, -60 %/2050.",
            reason_code="DT.APPLICABLE",
            confidence=1.0,
            missing_fields=[],
            evidence={"sdp_m2": site.sdp_m2, "usage": site.usage_principal},
            rule_version=self.version,
            computed_at=_now_iso(),
        )
```

### 4. Règles cataloguées (v1.0)

| Code | Scope | Sources | Critères assujettissement | Statut DATA_MISSING si |
|---|---|---|---|---|
| **DT** | site | Décret 2019-771 + arrêtés OPERAT | `site.sdp_m2 ≥ 1000` ET `usage ∈ tertiaire_set` | `sdp_m2` ou `usage_principal` null |
| **BACS** | site | Décret 2020-887 | `building.system_power_kw ≥ 70` (gradient 290→70 selon date) | `system_power_kw` null sur ≥ 1 bâtiment |
| **APER** | site | Loi 2023-175 art. 40 | `site.parking_m2 ≥ 1500` OU `site.is_industrial_roof ≥ 500m²` | `parking_m2` ou `roof_area` null |
| **SMÉ** | org | Code énergie L233-1 | `org.effectif ≥ 250` OU (`org.ca ≥ 50M€` ET `org.bilan ≥ 43M€`) | `effectif`, `ca`, `bilan` null |
| **BEGES** | org | Loi Grenelle 2 art. 75 | `org.effectif ≥ 500` (métropole) OU `≥ 250` (DOM) | `effectif`, `siege_dom` null |

### 5. Versioning des règles

```python
# backend/regulatory/rules_catalog.py

RULES_VERSIONS = {
    RuleCode.DT:    "DT-2019-771-v2024-10-01",
    RuleCode.BACS:  "BACS-2020-887-v2025-01-01",
    RuleCode.APER:  "APER-2023-175-v2024-07-01",
    RuleCode.SME:   "SME-L233-1-v2023-12-31",
    RuleCode.BEGES: "BEGES-Grenelle2-v2022-07-01",
}
```

**Politique de versioning** : tout changement de seuil (ex. BACS 290 → 70 kW) → nouvelle version + ADR + migration. La version est exposée dans `RuleApplicability.rule_version` et dans `footer.version_tags`.

### 6. Maturité patrimoine — agrégateur

```python
# backend/services/regulatory_applicability_service.py

def compute_patrimoine_maturity(db, org_id: int) -> float:
    """
    Renvoie un score 0.0..1.0 = pourcentage de champs critiques renseignés.

    Champs critiques (poids égaux v1.0) :
      org.effectif, org.ca, org.bilan, org.siege_dom
      site.sdp_m2, site.usage_principal, site.parking_m2, site.roof_area
      building.system_power_kw
    """
    fields_checked = 0
    fields_present = 0
    sites = _load_sites(db, org_id, None)
    org   = _load_org(db, org_id)

    for field in ["effectif", "ca", "bilan", "siege_dom"]:
        fields_checked += 1
        if getattr(org, field, None) is not None:
            fields_present += 1

    for site in sites:
        for field in ["sdp_m2", "usage_principal", "parking_m2", "roof_area"]:
            fields_checked += 1
            if getattr(site, field, None) is not None:
                fields_present += 1
        for building in site.buildings:
            fields_checked += 1
            if building.system_power_kw is not None:
                fields_present += 1

    return fields_present / fields_checked if fields_checked > 0 else 0.0
```

### 7. Endpoint d'inspection

```python
# backend/routes/regulatory_applicability.py

@router.get("/applicability")
def get_applicability(
    request: Request,
    site_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth = Depends(get_optional_auth),
):
    org_id = resolve_org_id(request, auth, db)
    applicability = compute_applicability(db, org_id, [site_id] if site_id else None)
    maturity      = compute_patrimoine_maturity(db, org_id)
    return {
        "applicability": applicability,
        "maturity":      maturity,
        "computed_at":   _now_iso(),
    }
```

Cet endpoint alimente le drawer "Mon cadre applicable" (frontend `<CadreApplicable />`) et permet aux tests/audits de vérifier la cohérence du moteur.

### 8. Tests source-guards obligatoires

```python
# backend/tests/source_guards/test_applicability_engine.py

def test_no_hardcoded_rule_status_outside_service(all_sources: list[str]):
    """Hors regulatory/ et services/regulatory_applicability_service.py,
    aucun fichier ne doit produire un ApplicabilityStatus."""
    forbidden = ['ApplicabilityStatus.APPLICABLE', 'ApplicabilityStatus.NOT_APPLICABLE',
                 '"status": "applicable"', '"status": "not_applicable"']
    allowed_paths = ["regulatory/", "services/regulatory_applicability_service",
                     "tests/", "doctrine/"]
    for src_path, content in all_sources:
        if any(p in src_path for p in allowed_paths):
            continue
        for f in forbidden:
            assert f not in content, f"Status hardcoded in {src_path}"

def test_every_rule_has_evaluator(rule_catalog: dict):
    for code in RuleCode:
        assert code in rule_catalog, f"Missing evaluator for {code}"

def test_data_missing_lists_concrete_fields():
    """DATA_MISSING ne peut être retourné sans missing_fields non vide."""
    for app in _all_test_outputs():
        if app.status == ApplicabilityStatus.DATA_MISSING:
            assert app.missing_fields, f"DATA_MISSING without fields for {app.rule}"
```

---

## Consequences

### Positives

1. **Source unique de vérité** : un seul service répond "ce site est-il assujetti ?", consommé par 6+ pages (Synthèse, Cockpit, Conformité, Patrimoine, Rapports, Onboarding)
2. **Traçabilité utilisateur** : chaque verdict a une phrase humaine et un code machine, exportables dans rapports
3. **Versioning** : changement de seuil = changement de version, audit trail garanti
4. **Différenciateur produit** : tooltip "pourquoi cette règle s'applique" = argument commercial vs Deepki/Metron qui hardcodent
5. **Onboarding intelligent** : `DATA_MISSING.missing_fields` alimente la wizard onboarding pour cibler les champs critiques

### Risques

1. **Catalogue à maintenir** : 5 règles v1.0, croît à 8-10 (CSRD, CBAM, ETS2, TDN) — `regulatory-expert` agent owner
2. **Drift sémantique des phrases** : `reason_human` est de la copy produit ; à figer dans i18n avant scaling
3. **Performance** : compute sur 100+ sites doit rester < 200 ms → mise en cache par `(org_id, rule_version)` avec invalidation sur write patrimoine

### Migration

- Phase 3.5 introduit le service avec 5 règles
- Migrer `compliance_score_service.py` pour consommer `compute_applicability` au lieu de relire la DB
- Migrer `routes/compliance.py` checks dispersés en `compute_applicability` upfront

---

## Implementation plan

### Phase 3.5 (cf. ADR-023, items 2)

| # | Item | Effort |
|---|---|---|
| 1 | `regulatory/applicability_types.py` + `RuleCode`, `ApplicabilityStatus` | 0.5 j/h |
| 2 | `regulatory/rules/dt.py` + `bacs.py` + `aper.py` + `sme.py` + `beges.py` | 2.5 j/h |
| 3 | `regulatory/rules_catalog.py` + dispatcher `RULE_EVALUATORS` | 0.5 j/h |
| 4 | `services/regulatory_applicability_service.py` + `compute_patrimoine_maturity` | 1 j/h |
| 5 | `routes/regulatory_applicability.py` endpoint + tests intégration | 0.5 j/h |
| 6 | Source-guards `test_applicability_engine.py` | 0.5 j/h |

**Total ≈ 5.5 j/h** Phase 3.5 (composant transverse).

---

## Open questions

1. **Décret tertiaire et statut UNKNOWN** : si un site déclare `usage_principal = "mixte"`, faut-il un statut `UNKNOWN` (cas usage tertiaire majoritaire) ou exiger une qualification ? Proposition : `UNKNOWN` v1.0, qualification fine v2.0.
2. **Multi-année OPERAT** : la trajectoire DT 2030 dépend de l'année de référence choisie (2010-2019) ; le moteur doit-il l'inclure ou est-ce un concern downstream du builder REGULATORY_DRIVEN ? Réponse : downstream — le moteur retourne juste `APPLICABLE` + SDP/usage, le builder compose la trajectoire.
3. **Surcharge manuelle** : un client peut-il forcer `NOT_APPLICABLE` malgré seuils franchis (ex. site en dérogation préfectorale) ? Proposition : champ `manual_override` sur `Site`, retournant `APPLICABLE` avec `confidence=0.5` et badge "à valider".

---

**Status** : `Proposed` — à acter par Amine en bloc avec ADR-023.

Auteur : session refonte Synthèse stratégique v3→v8 du 13/05/2026.
