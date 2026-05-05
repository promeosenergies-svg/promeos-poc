# ADR-011 — Type strict EnergieFinale kWhEF PCI

**Statut** : Accepté
**Date** : 2026-05-05
**Sprint** : C-4 Phase 4.3
**Personnes impliquées** : Amine (founder), Claude architect-helios + bill-intelligence + regulatory-expert
**Tracking dette** : `D-Sprint-C3-7d-EnergieFinale-Type-Strict-001` (P1 Sprint C-3 7d) → CLÔTURÉE Phase 4.3

---

## Contexte

`Site.annual_kwh_total` et autres champs énergie peuvent recevoir des valeurs hétérogènes mélangeables silencieusement : kWh énergie finale (EF) PCI, kWhEP (énergie primaire), MWh, kWh PCS gaz (GRDF), GWh (audits SMÉ). MVP Sprint C-3 Phase 3.4 = grep + commentaire `# kWhEF PCI` + source-guard `SG_KWHEF_01/02` allowlist.

**Limites MVP détectées** :

- SG allowlist regex limité : false negative `setattr(...)` Phase 3.4d audit
- Confusion kWhEF / kWhEP possible (coefficient 1.9 élec arrêté 10/04/2020 différencie les deux)
- GRDF R171 livre en kWh PCS (×0.901 pour PCI) — ingestion brute non typée
- AuditEnergetique livre en GWh (`conso_annuelle_moy_gwh`) — pas de helper conversion typé
- Risque shadow billing R20 (capacité variance > 5%) déclenché à tort si conso saisie en kWhEP

### Audit Phase 0 Phase 4.3 — diagnostic terrain

- **`backend/types/` n'existe pas** — création nouveau module
- **Aucun usage `Annotated[`/`NewType(`/`TypeDecorator`** dans `backend/models/` ni `backend/schemas/`
- **Pas de schema pydantic Site dédié** dans `backend/schemas/` (uniquement schemas billing/conformite/cockpit/etc.)
- Site SQLAlchemy : `annual_kwh_total = Column(Float, nullable=True, comment="Consommation annuelle totale (kWh)")`
- 7 autres champs énergie hétérogènes dans models : `tertiaire.kwh_total`, `tertiaire.normalized_kwh_total`, `tertiaire.conso_ep_kwh_m2_an` (kWhEP **distinct**), `audit_sme.conso_annuelle_moy_kwh`, `contract_v2.annual_kwh` (MWh comment), `billing.annual_consumption_kwh`, `usage.kwh_total`
- ~6 services consommateurs `Site.annual_kwh_total` : `intake_service`, `portfolio_intensity_service`, `operat_export_service`, `cee_service`, `compliance_readiness_service`, `compliance_rules`

---

## Décision

### Option retenue : **Option A enrichi pragmatique** (NewType + helpers conversion + typage signatures services)

Pas Option B (Annotated pydantic) qui nécessiterait création complète de schemas pydantic Site/AuditEnergetique/etc. (gros refactor hors scope MVP, risque casser runtime ORM). Pas Option C (TypeDecorator SQLAlchemy + dataclass) qui multiplie complexité runtime sans bénéfice MVP.

### 3 composants livrés

#### 1. Module `backend/promeos_types/energy.py` (nouveau)

```python
from typing import NewType

# kWh énergie finale PCI — unité cardinale PROMEOS pour conso facturée / mesurée
KwhEFPCI = NewType("KwhEFPCI", float)

# kWhEP — énergie primaire (différent de EF, coeff 1.9 élec arrêté 10/04/2020)
KwhEP = NewType("KwhEP", float)

# MWh énergie finale PCI — multiple courant gros consommateurs
MWhEFPCI = NewType("MWhEFPCI", float)

# GWh énergie finale PCI — multiple AuditEnergetique
GWhEFPCI = NewType("GWhEFPCI", float)

# kWh PCS gaz (GRDF natif — ×0.901 pour PCI)
KwhPCS = NewType("KwhPCS", float)


def gwh_to_kwh_ef_pci(gwh: GWhEFPCI | float) -> KwhEFPCI:
    """Convertit GWh → kWhEF PCI (×1_000_000)."""
    return KwhEFPCI(float(gwh) * 1_000_000)


def mwh_to_kwh_ef_pci(mwh: MWhEFPCI | float) -> KwhEFPCI:
    """Convertit MWh → kWhEF PCI (×1000)."""
    return KwhEFPCI(float(mwh) * 1000)


def kwh_pcs_to_kwh_ef_pci_gaz(kwh_pcs: KwhPCS | float) -> KwhEFPCI:
    """Convertit kWh PCS gaz GRDF → kWhEF PCI (coefficient 0.901)."""
    return KwhEFPCI(float(kwh_pcs) * 0.901)


def kwh_ef_to_kwh_ep_elec(kwh_ef: KwhEFPCI | float) -> KwhEP:
    """Convertit kWhEF élec → kWhEP via coefficient 1.9 (arrêté 10/04/2020)."""
    return KwhEP(float(kwh_ef) * 1.9)
```

#### 2. Typage signatures services consumers cardinaux (Phase 4.3 MVP)

Annotations `KwhEFPCI` posées sur les signatures publiques de :

- `services/portfolio_intensity_service.compute_portfolio_intensity()` — signature `sum_annual_kwh: KwhEFPCI`
- (autres services Sprint C-5+ via dette résiduelle)

Sites `annual_kwh_total` SQLAlchemy reste `Column(Float)` (compat ORM préservée). Le typage est **applicatif côté services** (catch confusion à la signature cross-module).

#### 3. Source-guard Phase 4.3 (en complément SG MVP Phase 3.4)

`backend/tests/source_guards/test_energy_types_strict_source_guards.py` (nouveau) :

- **SG_ENERGY_TYPES_01** : module `backend/promeos_types/energy.py` exporte les 5 NewType + 4 helpers documentés
- **SG_ENERGY_TYPES_02** : `portfolio_intensity_service` importe `KwhEFPCI` (typage signature consumer cardinal)
- **SG_ENERGY_TYPES_03** : helpers conversion `gwh_to_kwh_ef_pci` + `kwh_pcs_to_kwh_ef_pci_gaz` retournent bien `KwhEFPCI`

**Defense in depth** : SG Phase 3.4 conservés (`SG_KWHEF_01` allowlist setattr + `SG_KWHEF_02` commentaire). Combinaison robuste.

### Ce qui est explicitement HORS scope Phase 4.3

- ❌ Schemas pydantic Site complets (Sprint C-7 polish)
- ❌ TypeDecorator SQLAlchemy custom
- ❌ Migration runtime tous champs énergie autres modules (`tertiaire.kwh_total`, `audit_sme.conso_annuelle_moy_kwh`, etc.) — Sprint C-5 progressif
- ❌ Validation FastAPI request strict via pydantic (Sprint C-7+ après schemas Site créés)
- ❌ Refactor ingestion data_ingestion (GRDF kWh PCS → PCI) — déjà tracé `D-Sprint-C3-7d-EnergieFinale-Type-Strict-001` clôt + Sprint C-5+ pour conversion runtime

---

## Conséquences

### Positives

- **Différenciateur Bill Intelligence** : runtime types catch confusions kWhEF/kWhEP/GWh à la signature
- **Helpers conversion centralisés** : 1 SoT pour les coefficients réglementaires (×1.9, ×0.901, ×1000, ×1_000_000)
- **Defense in depth** : SG MVP + types signatures + helpers = 3 lignes de défense
- **Compat ORM préservée** : SQLAlchemy `Column(Float)` inchangé, pas de migration Alembic
- **Refactor incrémental possible** : Sprint C-5+ peut typer progressivement les autres services / champs
- **OpenAPI lisible (futur)** : Sprint C-7+ schemas pydantic Site exposeront le type kWhEFPCI dans Swagger

### Négatives / Compromis

- **NewType n'est PAS runtime check** : c'est un alias mypy-only. Le runtime accepte n'importe quel float. Mitigation : SG cardinal `SG_ENERGY_TYPES_02` vérifie l'usage cohérent dans services consumers
- **Migration progressive** : Phase 4.3 ne couvre QUE `portfolio_intensity_service` cardinal. Les autres services consumers (compliance_rules, cee_service, etc.) restent non typés MVP — dette résiduelle Sprint C-5
- **Coût cognitif** : devs doivent connaître la convention. Mitigation : module `backend/promeos_types/energy.py` documenté + ADR-011 cité dans CONTRIBUTING.md
- **Pas de validation pydantic FastAPI** : un client peut envoyer un kWhEP au lieu de kWhEF via API — Sprint C-7 polish via schemas pydantic dédiés

---

## Alternatives considérées

| Option | Pourquoi rejetée |
|---|---|
| **Option B — Annotated pydantic** sur Site/AuditEnergetique | Nécessite création schemas pydantic complets pour tous les modèles concernés — gros refactor non scopé MVP. Reporter Sprint C-7. |
| **Option C — TypeDecorator SQLAlchemy + dataclass runtime** | Complexité runtime élevée vs bénéfice MVP. À considérer si Sprint C-7 schemas pydantic + besoin runtime validation persistante. |
| **Status quo (SG MVP Phase 3.4 seul)** | False negatives `setattr` détectés Phase 3.4d. Pas de typage signatures = confusion possible cross-services. Pas de helpers conversion = duplication coefficients ×1.9 / ×0.901. |
| **Migration immédiate tous champs énergie** | Scope creep Phase 4.3. Risque casser ~13 tests existants + 6 services consumers. Migration progressive Sprint C-5+. |
| **Validation runtime via décorateurs custom** | Surcoût CPU + complexité maintenance. NewType + SG + typage signatures suffisant MVP. |

---

## Statut & validation

- **Acceptée** : 2026-05-05 (Sprint C-4 Phase 4.3)
- **Implémentation** : commit dédié Phase 4.3 (NewType module + helpers + typage `portfolio_intensity_service` + 3 SG)
- **Sprint C-5+** : extension typage progressive (compliance_rules, cee_service, intake_service)
- **Sprint C-7 polish** : schemas pydantic Site/AuditEnergetique avec `Annotated[KwhEFPCI, Field(...)]` + validation FastAPI request

Closes (post-implémentation Phase 4.3) : `D-Sprint-C3-7d-EnergieFinale-Type-Strict-001` P1.

Nouvelle dette résiduelle ouverte : `D-Phase4-3-Energy-Types-Migration-Progressive-001` P1 Sprint C-5 (typage progressif autres services consumers).

---

## Mise à jour Phase 4.3d audit follow-up (2026-05-05)

Audit multi-agents post-Phase 4.3 (regulatory-expert + code-reviewer + /simplify) → 1 finding P0 doctrinal critique + 3 P1/P2.

### P0 doctrinal critique (regulatory-expert)

**Source revendiquée fausse + valeur fantôme** : `COEFF_KWH_EF_TO_KWH_EP_ELEC = 1.9` cite l'arrêté 10/04/2020 art. 2-g (NOR LOGL2005904A) qui définit l'**énergie finale** uniquement et **ne contient AUCUN PEF élec**. OPERAT raisonne exclusivement en kWhEF (pas EP). La valeur 1.9 n'est pas un coefficient officiel français connu (PEF élec officiel : **2.3** RE2020 arrêté 04/08/2021 NOR LOGL2107359A, ou **2.58** RT2012 historique).

### Décision Phase 4.3d (Option A2 — suppression)

Suppressions dans `backend/promeos_types/energy.py` :

| Élément | Justification |
|---|---|
| `COEFF_KWH_EF_TO_KWH_EP_ELEC = 1.9` | Valeur fantôme — pas source officielle FR |
| `kwh_ef_to_kwh_ep_elec()` helper | Aucun consumer + OPERAT raisonne en EF (pas EP) |
| `KwhEP` NewType | Plus utilisé après suppression helper |
| `MWhEFPCI` NewType + `mwh_to_kwh_ef_pci()` + `kwh_ef_to_mwh()` + `kwh_ef_to_gwh()` | YAGNI cleanup (aucun consumer, /simplify S5 recommandation) |
| `FACTOR_MWH_TO_KWH = 1000` | Cleanup associé MWhEFPCI suppression |

### État final post-4.3d (cardinal MVP)

| Catégorie | Avant 4.3d | Après 4.3d |
|---|---|---|
| NewType | 5 | **3** (KwhEFPCI, GWhEFPCI, KwhPCS) |
| Helpers conversion | 6 | **2** (gwh_to_kwh_ef_pci, kwh_pcs_to_kwh_ef_pci_gaz) |
| Coefficients réglementaires | 4 | **2** (COEFF_KWH_PCS_TO_KWH_PCI_GAZ, FACTOR_GWH_TO_KWH) |

### Nouveautés Phase 4.3d

- **Edge case guards** : helper interne `_validate_finite_non_negative()` rejette NaN / Inf / valeurs négatives (énergie ≥ 0 doctrinal). Appliqué sur les 2 helpers conservés.
- **6 tests edge cases** : `test_promeos_types_energy.py` couvre négatif/NaN/Inf pour chacun des 2 helpers.
- **SG `_REQUIRED_*` aligné** sur cardinal MVP (3 NewType / 2 helpers / 2 coefficients).
- **ADR-011 path corrigé** : `backend/types/energy.py` → `backend/promeos_types/energy.py` (3 occurrences — divergence ADR vs code détectée code-reviewer P1).

### Si besoin Sprint C-5+ : réintroduction PEF élec RE2020

Si un consumer Sprint C-5+ requiert la conversion EF→EP (reporting CSRD / DPE / RE2020) :

1. Source PDF arrêté 04/08/2021 NOR LOGL2107359A à committer dans `docs/sources/regulatory/re2020/`
2. Réintroduire `COEFF_KWH_EF_TO_KWH_EP_ELEC = 2.3` (valeur officielle RE2020)
3. Réintroduire `KwhEP` + `kwh_ef_to_kwh_ep_elec()` avec docstring corrigé (citer arrêté 04/08/2021, **pas** OPERAT 10/04/2020)
4. SG cohérence YAML ↔ valeur 2.3 + tests edge cases

### Discipline KB MEMORY tenue

- "0 chiffre sans source affirmée" (ADR-010 Phase 4.2d) — coefficient fantôme supprimé
- "1 SoT par concept" (doctrine Sol §6.4) — coefficients restants tous sourcés
- Pattern audit multi-agents 5e application Phase C (ROI cumulé : ~17 fixes intra-sprint, ~22 dettes tracées)

### Note utilisateur

⚠️ La mémoire user "Coeff énergie primaire élec = 1.9" (mémoire interne ou notes) est **incorrecte** et à retirer. Valeurs officielles FR : **2.3** RE2020 (depuis 01/01/2022) ou **2.58** RT2012 (historique).
