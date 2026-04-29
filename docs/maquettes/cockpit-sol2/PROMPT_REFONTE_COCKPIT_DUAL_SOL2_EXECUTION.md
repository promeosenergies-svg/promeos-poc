# PROMPT REFONTE COCKPIT DUAL SOL2 — exécution

> **Mission** : refondre le Cockpit dual (page de Pilotage + page de Synthèse stratégique) selon doctrine PROMEOS Sol v1.0 + arbitrages Amine 2026-04-28.
>
> **Périmètre** : 7 semaines · 5 phases · ~50 source-guards pytest · 12 KPI doctrinalement justifiés · 2 mockups cibles validés (`cockpit_pilotage_final_sol2_phase2` + `cockpit_decision_final_sol2_phase2`).
>
> **Méthodologie** : audit-first (déjà fait — bilan `AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md` reçu) · phases atomiques · hard STOP gate à chaque phase · MCP Context7 + code-review + simplify obligatoires · zéro régression.
>
> **Statut** : prompt d'exécution Sprint Refonte Cockpit Dual Sol2. Successeur de `PROMPT_AUDIT_VUE_EXECUTIVE_SOL2.md`. À ne pas confondre avec un audit — ici on **modifie le code de production**, sous gate stricte.

---

## 0. Hard STOP gate global — prérequis non-négociables

### 0.A — État du repo

```bash
git status
git rev-parse --abbrev-ref HEAD
```

**STOP si** : git status non clean (au-delà des fichiers `docs/audit/agent_sessions.jsonl` et `.claude/scheduled_tasks.lock` connus comme harness) · branche ≠ `claude/refonte-sol2`.

### 0.B — MCP plugins obligatoires

- **Context7** (documentation up-to-date) — chaque session
- **code-review** (revue critique avant commit) — chaque phase
- **simplify** (détection sur-ingénierie) — chaque phase

**STOP si l'un des trois n'est pas disponible.**

### 0.C — Tests pré-sprint verts

```bash
cd backend && python -m pytest --co -q | tail -3
cd ../frontend && npx vitest run --reporter=dot 2>&1 | tail -5
```

Baseline attendue : 5 861 BE collected · 4 237 FE passed · 1 FE échec pré-existant `CxDashboardPage.test.js` (hors périmètre, autorisé). **STOP si dégradation au-delà de cette baseline.**

### 0.D — Décisions Amine actées

Toutes les décisions Q1-Q10 du bilan d'audit Vue Exécutive sont actées. Récap :

| # | Décision actée | Phase concernée |
|---|---|---|
| Q1 | Leviers en MWh/an via `_savings_kwh / 1000`, suppression heuristique 8500 € | Phase 2 |
| Q2 | Créer endpoint `/api/purchase/cost-simulation/portfolio/{org_id}` agrégeant 5 sites | Phase 1 |
| Q3 | Bandeau Pilotage usages → split : 1 KPI agrégé Décision + détails sur page Flex Intelligence | Phase 0 |
| Q4 | Audit seed bâtiment : `SELECT site_id, COUNT(*), SUM(surface_m2) FROM batiment GROUP BY site_id` puis correction | Phase 1 |
| Q5 | Trajectoire DT lissée par `action.echeance` (gain réparti dans le temps réel) | Phase 1 |
| Q6 | Dictionnaire `acronym_to_narrative.py` centralisé · 12 entrées | Phase 1 |
| Q7 | Seed `created_at` réparti sur 7 j pour notifications | Phase 1 |
| Q8 | Drill-downs KPI hero : Trajectoire → Conformité, Exposition → 3 sites NC, Leviers → /actions filtrées | Phase 3 |
| Q9 | Décommissionner `ExecutiveKpiRow` + `ImpactDecisionPanel`, garder `<SolBriefingHead>` triptyque | Phase 0 |
| Q10 | Leak Hypermarché Montreuil (slug `retail-001` hardcodé) traité dans Phase 0 (fix 5 min, ne bloque pas Sprint A org-scoping) | Phase 0 |

**Décisions complémentaires Amine (28/04/2026) :**

| # | Décision | Phase |
|---|---|---|
| A | Tout € traçable réglementaire (article cité) ou contractuel (contrat_id), sinon disparition en énergie | Phase 1 + Phase 2 |
| B | 3 baselines distinctes : A historique brute · B DJU-ajustée (E=a×DJU+b) · C réglementaire DT (`ref_year=2020`) | Phase 1 |
| C | Modèle `EurAmount` typé avec category obligatoire | Phase 1 |
| D | Modèle `BaselineCalibration` avec r², calibration_date, méthode | Phase 1 |
| E | Phase 4 = test utilisateur réel (2 dirigeants 3 min + 2 energy managers 30 s) | Phase 4 |
| F | Phase 5 = mesure continue Playwright J vs J+1 + analytics drill-downs | Phase 5 |

### 0.E — Doctrine Cockpit dual v1 (extrait)

**Principes inviolables pendant le sprint :**

1. Le Tableau de bord (Briefing du jour) est une **page de pilotage** — energy manager · 30 s · « quoi traiter aujourd'hui »
2. La Vue Exécutive (Synthèse stratégique) est une **page de décision** — dirigeant non-sachant · 3 min · « où en sommes-nous, quoi décider »
3. **Source de vérité unique** : mêmes endpoints atomiques `_facts`, projections éditoriales différenciées
4. **Pas un empilement de widgets** : ≤ 7 blocs visibles à l'ouverture sur chaque vue
5. **3 KPI hero maximum** par vue
6. **Push événementiel** : narrative évolue J vs J+1, mention « +X vs S-1 » sur Décision
7. **Réciprocité Décision ⇄ Pilotage** : chaque KPI exécutif a un drill-down preuve op, chaque alerte op > seuil a un lien Décision
8. **Centre d'action** est le lien naturel entre les deux vues

**Constantes inviolables (rappel) :**
- CO₂ électricité = 0,052 kgCO₂/kWh (ADEME Base Empreinte V23.6)
- CO₂ gaz = 0,227 kgCO₂/kWh
- ⚠️ 0,0569 = TURPE 7 HPH €/kWh, **jamais CO₂**
- Coef énergie primaire élec = 1,9 (depuis janv 2026)
- Prix fallback = 0,068 €/kWh (jamais 0,18)
- Accise élec fév 2026+ : T1 30,85 €/MWh / T2 26,58 €/MWh
- Accise gaz fév 2026+ : 10,73 €/MWh
- DT jalons : −40 % / 2030 · −50 % / 2040 · −60 % / 2050
- DT pénalité : 7 500 € / 3 750 € (A_RISQUE)
- NEBCO seuil : 100 kW par pas de pilotage
- OID office benchmark : ~146 kWhEF/m²/an
- Audit énergétique seuils : 2,75 GWh / 23,6 GWh, deadline 11/10/2026

### 0.F — Périmètre fichiers autorisés en écriture

**Production code** (modifications autorisées) :
- `backend/services/`, `backend/routes/`, `backend/models/`, `backend/doctrine/`
- `frontend/src/pages/cockpit/`, `frontend/src/pages/Cockpit.jsx`, `frontend/src/pages/CommandCenter.jsx`
- `frontend/src/components/cockpit/` et composants Sol partagés
- `frontend/src/services/api/cockpit.js`, `pilotage.js`, `purchase.js`
- `backend/tests/`, `frontend/src/__tests__/`
- `backend/services/demo_seed/` pour seeds HELIOS

**Documentation** :
- `docs/audits/`, `docs/decisions/`, `docs/sprints/SPRINT_COCKPIT_DUAL_SOL2.md`

**INTERDIT pendant le sprint** :
- Toute modification `frontend/src/pages/admin/` (zone hors-périmètre)
- Toute modification `backend/routes/admin*` (zone hors-périmètre)
- Toute modification de `.github/workflows/` ou CI sans validation explicite
- Tout `git push --force` sur `claude/refonte-sol2`

### 0.G — Convention de commit

Chaque phase produit **N commits atomiques** :

```
feat(cockpit-sol2): Phase X.Y — description courte

- Bullet point 1 (fichier modifié + raison)
- Bullet point 2
- Source-guards ajoutés : test_xxx, test_yyy

Doctrine compliance: §X.Y (principe N)
Refs: AUDIT_VUE_EXECUTIVE_SOL2_BILAN.md §Z
```

Aucun commit ne dépasse 500 lignes diff (sauf migration mécanique). Si > 500 lignes : split en sous-commits.

---

## 1. Phase 0 — Épuration visuelle (semaine 1)

### 1.A — Objectif

Faire de la place. Ne rien réparer, juste enlever ce qui pollue la vue. C'est la condition pour que les phases suivantes soient lisibles et que les bugs deviennent visibles.

### 1.B — Backlog atomique

#### Phase 0.1 — Décommission `ExecutiveKpiRow` (Q9)

```bash
# Audit usage
grep -rn "ExecutiveKpiRow" frontend/src/ --include="*.{js,jsx,ts,tsx}"
```

- Supprimer composant `frontend/src/pages/cockpit/ExecutiveKpiRow.jsx`
- Supprimer import dans `Cockpit.jsx`
- Supprimer tests dédiés (s'il en existe)
- Snapshot test `<SolBriefingHead>` : confirmer que le triptyque hero reste visible

**Commit** : `feat(cockpit-sol2): Phase 0.1 — décommission ExecutiveKpiRow legacy (Q9)`

#### Phase 0.2 — Décommission `ImpactDecisionPanel` (Q9)

```bash
grep -rn "ImpactDecisionPanel\|impactDecisionModel" frontend/src/ --include="*.{js,jsx,ts,tsx}"
```

- Supprimer `frontend/src/pages/cockpit/ImpactDecisionPanel.jsx`
- Supprimer `frontend/src/models/impactDecisionModel.js` (sera reconstruit en backend Phase 1.4)
- Supprimer import dans `Cockpit.jsx`
- Migrer logique métier essentielle (3 KPI Risque/Surcoût/Optim) vers backend `services/cockpit_decision_service.py` **MAIS** pas dans cette phase — juste documenter ce qui doit être migré.

**Commit** : `feat(cockpit-sol2): Phase 0.2 — décommission ImpactDecisionPanel + heuristiques frontend (Q9)`

#### Phase 0.3 — Plier bandeau Pilotage usages (Q3)

- Conserver UNIQUEMENT 1 card teaser avec narrative agrégée :
  ```
  Gisement Flex portefeuille — 21 k€/an identifié sur 5 sites.
  Activation possible via partenaire d'agrégation.
  [Voir Flex Intelligence →]
  ```
- Supprimer de la Vue Exé : Radar fenêtres favorables, Gain annuel Flex Ready® détaillé, Heatmap archétype, Classement portefeuille top 5
- Ces composants restent disponibles sur la **page Flex Intelligence** (route `/flex` ou équivalent) — vérifier qu'ils sont déjà câblés ou les déplacer
- Le chiffre `21 k€/an` doit être typé `EurAmount` catégorie B contractuel **OU** affiché en MWh/an si pas de contrat — décision en Phase 2

**Commit** : `feat(cockpit-sol2): Phase 0.3 — plier bandeau Pilotage usages en card teaser (Q3)`

#### Phase 0.4 — Suppression cards mortes

- Card « Bienvenue PROMEOS » → supprimer
- Card « Gain simulé empty » (« CDC du site non seedée — contactez votre CSM ») → supprimer
- Card `BriefCodexCard` détaillée → conserver mais sous toggle `expert` par défaut fermé (déjà le cas en partie)

**Commit** : `feat(cockpit-sol2): Phase 0.4 — suppression cards mortes anti-pattern §6.3`

#### Phase 0.5 — Replier composantes facture inactives (VNU + CBAM)

Sur la facture prévisionnelle Vue Exé :
- Lignes `VNU` (dormant) et `CBAM` (non applicable) : déplacer derrière `<details>` avec summary mono « + Composantes inactives · 2 lignes »
- Conserver dans la décomposition principale : Fourniture · TURPE 7 · Capacité · Taxes

**Commit** : `feat(cockpit-sol2): Phase 0.5 — collapse composantes facture inactives sous details`

#### Phase 0.6 — Fix leak Hypermarché Montreuil (Q10)

```bash
grep -rn "retail-001\|tour-001\|entrepot-001" frontend/src/pages/cockpit/ frontend/src/pages/Cockpit.jsx --include="*.{js,jsx,ts,tsx}"
```

- Identifier le composant qui hardcode `retail-001` dans la card Flex Ready de la Vue Exé
- Remplacer par une logique conditionnelle :
  - Si scope HELIOS → afficher KPI agrégé portefeuille (cf. Phase 0.3)
  - Si scope Flex demo (route `/flex`) → conserver `retail-001` comme exemple type
- Supprimer toute référence `retail-001`/`tour-001`/`entrepot-001` du DOM rendu en scope HELIOS

**Source-guard à créer** : `test_helios_no_demo_sites_leak`
```python
def test_helios_no_demo_sites_leak(authed_client_helios):
    """Aucun slug demo Flex (retail-001/tour-001/entrepot-001) ne doit
    apparaître dans la réponse de la Vue Exécutive en scope HELIOS."""
    response = authed_client_helios.get("/api/pages/cockpit_comex/briefing")
    body = response.text
    assert "retail-001" not in body
    assert "tour-001" not in body
    assert "entrepot-001" not in body
```

**Commit** : `fix(cockpit-sol2): Phase 0.6 — leak Hypermarché Montreuil (Q10) + source-guard`

### 1.C — Definition of Done Phase 0

- [ ] `<ExecutiveKpiRow>` et `<ImpactDecisionPanel>` supprimés du rendu Cockpit.jsx
- [ ] `frontend/src/models/impactDecisionModel.js` supprimé (migration backend documentée pour Phase 1.4)
- [ ] Bandeau Pilotage usages = 1 card teaser (vs 4 cards précédemment)
- [ ] 0 référence `retail-001`/`tour-001`/`entrepot-001` dans rendu HTML scope HELIOS
- [ ] Cards mortes supprimées (Bienvenue PROMEOS, Gain simulé empty)
- [ ] VNU + CBAM collapsées sous `<details>`
- [ ] Source-guard `test_helios_no_demo_sites_leak` ✅
- [ ] Snapshot Vue Exé : ≤ 10 composants enfants visibles (vs 28 actuels)
- [ ] Tests pytest 5 861 + Vitest 4 237 (baseline) maintenus
- [ ] 6 commits atomiques (Phase 0.1 à 0.6)

### 1.D — Capture de progression

```bash
node tools/playwright/audit-vue-executive-sol2.mjs --output=docs/sprints/captures/phase-0-end
```

Comparer captures `phase-0-end/` vs initial pour mesurer densité visuelle (objectif ≤ 7 blocs visibles à l'ouverture).

---

## 2. Phase 1 — Backend rigoureux (semaines 2-4)

### 2.A — Objectif

Construire les fondations propres : source unique atomique, traçabilité euros, calculs de baseline rigoureux, dictionnaire acronymes, migration logique métier frontend → backend.

### 2.B — Backlog atomique

#### Phase 1.1 — Modèle `EurAmount` typé (décision A)

**Modèle SQLAlchemy** : `backend/models/eur_amount.py`

```python
from sqlalchemy import Column, Integer, Float, String, ForeignKey, Enum, DateTime
from enum import Enum as PyEnum

class EurAmountCategory(PyEnum):
    CALCULATED_REGULATORY = "calculated_regulatory"
    CALCULATED_CONTRACTUAL = "calculated_contractual"
    # PAS de "modeled" ni "estimated" — interdits par doctrine

class EurAmount(Base):
    __tablename__ = "eur_amounts"
    id = Column(Integer, primary_key=True)
    value_eur = Column(Float, nullable=False)
    category = Column(Enum(EurAmountCategory), nullable=False)
    regulatory_article = Column(String, nullable=True)  # ex: "Décret 2019-771 art. 9"
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    formula_text = Column(String, nullable=False)  # ex: "3 × 7500 + 1 × 3750"
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Contrainte : exactement un de (regulatory_article, contract_id) non null selon category
    __table_args__ = (
        CheckConstraint(
            "(category = 'calculated_regulatory' AND regulatory_article IS NOT NULL) OR "
            "(category = 'calculated_contractual' AND contract_id IS NOT NULL)",
            name="eur_amount_traceability_check"
        ),
    )
```

**Service** : `backend/services/eur_amount_service.py`
- `build_regulatory(value, article, formula)` → `EurAmount`
- `build_contractual(value, contract_id, formula)` → `EurAmount`
- `to_dict_with_proof(eur_amount)` → dict pour API avec champ `proof_url`

**Source-guards** :
- `test_eur_amount_typed` — aucun champ `*_eur` dans réponses API n'est un float nu
- `test_eur_amount_traceability` — chaque EurAmount a soit `regulatory_article` soit `contract_id` non null
- `test_no_modeled_eur_amount` — aucune entrée DB avec category `modeled` ou `estimated`

**Endpoint proof** : `GET /api/cockpit/eur_amount/{id}/proof` retourne le détail traçable pour tooltip front.

**Commit** : `feat(cockpit-sol2): Phase 1.1 — modèle EurAmount typé + traçabilité (décision A)`

#### Phase 1.2 — Service `baseline_service.py` (décision B+D)

**Modèle SQLAlchemy** : `backend/models/baseline_calibration.py`

```python
class BaselineMethod(PyEnum):
    A_HISTORICAL = "a_historical"  # moyenne 4 mêmes jours sur 12 semaines
    B_DJU_ADJUSTED = "b_dju_adjusted"  # E = a×DJU + b
    C_REGULATORY_DT = "c_regulatory_dt"  # ref_year fixée

class BaselineCalibration(Base):
    __tablename__ = "baseline_calibrations"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    method = Column(Enum(BaselineMethod), nullable=False)
    calibration_date = Column(DateTime, nullable=False)
    coefficient_a = Column(Float, nullable=True)  # méthode B
    coefficient_b = Column(Float, nullable=True)  # méthode B
    ref_year = Column(Integer, nullable=True)  # méthode C
    r_squared = Column(Float, nullable=True)  # méthode B
    data_points = Column(Integer, nullable=False)
    confidence = Column(String, nullable=False)  # haute/moyenne/faible auto
```

**Service** : `backend/services/baseline_service.py`

```python
def get_baseline_a(site_id: int, target_date: date) -> dict:
    """Baseline A : moyenne 4 mêmes jours de semaine sur 12 semaines glissantes."""
    # Retourne {value_kwh, calibration_date, confidence, method: "a_historical"}

def get_baseline_b(site_id: int, target_date: date, dju: float) -> dict:
    """Baseline B : E = a×DJU + b calibré sur 12 mois glissants.
    Si moins de 90 jours data : fallback get_baseline_a.
    Si r² < 0.7 : confidence='faible'."""
    # Retourne {value_kwh, calibration_date, confidence, r_squared, a, b, method: "b_dju_adjusted"}

def get_baseline_c(site_id: int, year: int) -> dict:
    """Baseline C : conso année référence DT (ref_year=2020 pour HELIOS)."""
    # Retourne {value_kwh_year, ref_year, method: "c_regulatory_dt"}
```

**Job de re-calibration** : `backend/jobs/baseline_calibration_job.py`
- Déclencheur : tous les 7 j pour méthode B (recalibre coefficients), tous les ans pour méthode C
- Stocke nouvelle `BaselineCalibration` (historique conservé)

**Seed HELIOS** : `backend/services/demo_seed/gen_baseline.py`
- 12 mois de DJU pour 5 communes (Paris, Lyon, Marseille, Nice, Toulouse) — déterministe via seed RNG=42
- Calibration baseline B initiale pour les 5 sites avec coefficients cohérents archetype
- Calibration baseline C initiale avec `ref_year=2020`

**Source-guards** :
- `test_baseline_method_documented` — tout endpoint retournant écart vs baseline retourne aussi `baseline_method`, `calibration_date`, `confidence`
- `test_baseline_r_squared_threshold` — si `r_squared < 0.7`, badge confiance retourné = `faible`
- `test_no_baseline_computation_in_frontend` — grep `baseline.*=` dans `frontend/src/pages/cockpit/*.jsx` → 0 résultat
- `test_baseline_a_fallback` — si moins de 90 j data, méthode B fallback en méthode A

**Commit** : `feat(cockpit-sol2): Phase 1.2 — service baseline_service avec 3 méthodes A/B/C (décisions B+D)`

#### Phase 1.3 — Endpoint atomique `_facts` partagé (source unique réelle)

**Endpoint** : `GET /api/cockpit/_facts?org_id={id}&period={current_week|current_month|current_year}`

Retourne tous les faits atomiques nécessaires aux 2 vues :

```json
{
  "scope": {
    "org_id": 1,
    "org_name": "Groupe HELIOS",
    "site_count": 5,
    "site_ids": [1, 2, 3, 4, 5],
    "surface_total_m2": 17500,  // après fix Phase 1.5
    "ref_year": 2020
  },
  "consumption": {
    "j_minus_1_mwh": 9.3,
    "baseline_j_minus_1": {"value_mwh": 8.4, "method": "a_historical", "delta_pct": 11},
    "surconso_7d_mwh": 4.7,
    "baseline_7d": {"method": "b_dju_adjusted", "r_squared": 0.87, "calibration_date": "2026-04-20"},
    "sites_in_drift": 2,
    "annual_mwh": 4229,
    "trajectory_2030_score": 37,
    "trajectory_method": "c_regulatory_dt"
  },
  "power": {
    "peak_j_minus_1_kw": 528,
    "subscribed_kw": 480,
    "delta_pct": 10,
    "peak_time": "11:30"
  },
  "compliance": {
    "score": 37,
    "max": 100,
    "weighting": {"DT": 0.45, "BACS": 0.30, "APER": 0.25},
    "non_conform_sites": 1,
    "at_risk_sites": 2,
    "obligations_to_treat": 11
  },
  "exposure": {
    "total": {"value_eur": 26200, "category": "calculated_regulatory", "regulatory_article": "Décret 2019-771 art. 9"},
    "delta_vs_last_week": {"value_eur": 3800, "category": "calculated_regulatory"},
    "components": [
      {"label": "DT non conforme", "count": 1, "unit_value_eur": 7500, "value_eur": 7500, "regulatory_article": "Décret 2019-771 art. 9"},
      {"label": "DT à risque", "count": 4, "unit_value_eur": 3750, "value_eur": 15000, "regulatory_article": "Décret 2019-771 art. 9"},
      {"label": "BACS non conforme", "count": 1, "unit_value_eur": 1500, "value_eur": 1500, "regulatory_article": "Décret 2020-887"},
      {"label": "OPERAT manquante", "count": 1, "unit_value_eur": 1500, "value_eur": 1500, "regulatory_article": "Circulaire DGEC 2024"}
    ]
  },
  "potential_recoverable": {
    "value_mwh_year": 245,
    "method": "modeled_cee",
    "references": ["CEE BAT-TH-116", "CEE BAT-TH-104"],
    "leverage_count": 3,
    "by_lever": [
      {"name": "Système pilotage CVC Siège", "value_mwh_year": 115, "reference": "CEE BAT-TH-116"},
      {"name": "Audit énergétique 5 sites", "value_mwh_year": 130, "reference": "Code Énergie L233-1"}
    ]
  },
  "alerts": {
    "total": 11,
    "by_severity": {"critical": 3, "high": 4, "medium": 4},
    "by_type": {"anomaly": 4, "compliance": 3, "data_quality": 2, "tariff": 2}
  },
  "data_quality": {
    "ems_coverage_pct": 100,
    "data_completeness_pct": 94,
    "missing_indices_24h": 2,
    "sites_with_gaps": ["Toulouse"]
  },
  "metadata": {
    "last_update": "2026-04-27T12:00:00Z",
    "confidence": "haute",
    "sources": ["RegOps", "RegAssessment", "EMS", "Décret 2019-771"]
  }
}
```

**Service** : `backend/services/cockpit_facts_service.py`
- Centralise les appels à `KpiService`, `compliance_score_service`, `baseline_service`, `eur_amount_service`
- **Aucune duplication** : `narrative_generator.py` consomme désormais `_facts` au lieu de recalculer

**Source-guards** :
- `test_cockpit_facts_unique_source` — `briefing_daily` et `briefing_comex` consomment exactement le même `_facts`, snapshot des KPI partagés bit-à-bit identique
- `test_cockpit_facts_no_recompute` — grep AST sur `narrative_generator.py` : aucun appel direct à `KpiService.get_*` (passe par `_facts`)
- `test_cockpit_facts_dt_penalty_doctrine` — `exposure.components` utilise `DT_PENALTY_EUR` doctrine (7500), pas littéral

**Commit** : `feat(cockpit-sol2): Phase 1.3 — endpoint atomique _facts partagé (source unique réelle)`

#### Phase 1.4 — Migration `models/*.js` → `services/*.py`

Migration des 5 fichiers JS vers backend :

| Fichier JS supprimé | Service Python créé | Endpoint exposant |
|---|---|---|
| `models/impactDecisionModel.js` | `services/impact_decision_service.py` | `/api/cockpit/impact_decision` |
| `models/leverEngineModel.js` | `services/lever_engine_service.py` | `/api/cockpit/levers` |
| `models/dashboardEssentials.js` | `services/dashboard_essentials_service.py` | `/api/cockpit/essentials` |
| `models/priorityModel.js` | `services/priority_service.py` | `/api/cockpit/priorities` |
| `models/dataActivationModel.js` | `services/data_activation_service.py` | `/api/cockpit/data_activation` |

Pour chaque migration :
1. Lire JS, identifier toutes les fonctions et constantes
2. Réécrire en Python avec tests pytest unitaires (1:1 sur les cas couverts par tests JS si existants)
3. Exposer via endpoint dédié
4. Mettre à jour le composant front pour appeler l'endpoint au lieu de faire le calcul
5. Source-guard : grep `Math\.round\|reduce\|aggregate` dans `frontend/src/pages/cockpit/*.jsx` < 5 occurrences (vs 15 actuellement)
6. Supprimer le fichier JS

**Source-guard** : `test_no_business_logic_in_frontend_cockpit`
```python
def test_no_business_logic_in_frontend_cockpit():
    """Limite stricte de calculs dans les composants Cockpit."""
    forbidden_patterns = [r"Math\.round.*\+.*reduce", r"sum.*=.*0", r"aggregate"]
    cockpit_files = glob("frontend/src/pages/cockpit/*.jsx")
    violations = []
    for f in cockpit_files:
        content = open(f).read()
        for pattern in forbidden_patterns:
            if re.search(pattern, content):
                violations.append(f"{f}: {pattern}")
    assert len(violations) <= 5, f"Trop de logique métier frontend: {violations}"
```

**Commit** : `refactor(cockpit-sol2): Phase 1.4 — migration 5 models JS → services Python (Q9 + décision F)`

> ⚠️ Cette phase est la plus lourde (~1500 lignes JS à migrer). Si déborde, splitter en 5 sous-phases (1.4.a à 1.4.e), une par fichier.

#### Phase 1.5 — Audit & correction surface bâtiment (Q4)

```bash
# Diagnostic
sqlite3 promeos.db "SELECT site_id, COUNT(*) AS nb_batiments, SUM(surface_m2) AS surface_total FROM batiment GROUP BY site_id;"
```

Si `nb_batiments > 1` par site (et c'est le cas suspecté = 2 bâtiments × 3 500 m² = 7 000 m² par site × 5 sites = 35 000 m²) :
- **Décision attendue Amine** : corriger seed pour 1 bâtiment / site **OU** documenter explicitement que SHON OPERAT ≠ surface utile
- Si correction seed : `gen_batiment.py` modifié pour 1 bâtiment / site avec surface utile correcte
- Si SHON : ajouter champ `surface_utile_m2` distinct de `surface_m2` (=SHON), et utiliser `surface_utile_m2` pour les KPI kWh/m²/an

Cible : surface_total_m2 = **17 500 m²** pour HELIOS (3 500 + 1 200 + 2 800 + 4 000 + 6 000 = 17 500).

**Source-guard** : `test_helios_surface_total`
```python
def test_helios_surface_total(authed_client_helios):
    response = authed_client_helios.get("/api/cockpit/_facts?period=current_year")
    assert response.json()["scope"]["surface_total_m2"] == 17500
```

**Commit** : `fix(cockpit-sol2): Phase 1.5 — surface bâtiment HELIOS 35000 → 17500 m² (Q4)`

#### Phase 1.6 — Lissage trajectoire DT par échéance (Q5)

Modifier `backend/routes/cockpit.py:546-557` :

```python
# AVANT (bug drop -43 %)
_savings_kwh = sum(a.estimated_gain_eur or 0 for a in actions) / DEFAULT_PRICE_ELEC_EUR_KWH
projection_mwh.append(max(0, round((_lr - _savings_kwh) / 1000, 1)))  # tout en 2026

# APRÈS (lissé par échéance)
def project_with_action_echeances(reel_baseline_mwh: float, actions: list, target_year: int) -> float:
    """Projection trajectoire qui répartit les gains selon échéance réelle de chaque action."""
    cumul_savings_mwh = 0
    for action in actions:
        if action.echeance and action.echeance.year <= target_year:
            gain_mwh = (action.estimated_gain_eur or 0) / DEFAULT_PRICE_ELEC_EUR_KWH / 1000
            # Lissage : gain s'applique progressivement à partir de l'échéance
            months_active = max(0, 12 - (action.echeance.month - 1)) if action.echeance.year == target_year else 12
            cumul_savings_mwh += gain_mwh * (months_active / 12)
    return max(0, reel_baseline_mwh - cumul_savings_mwh)
```

**Source-guard** : `test_trajectory_smoothed_by_echeance`
```python
def test_trajectory_smoothed_by_echeance(authed_client_helios):
    """Aucun drop > 15% YoY sur la projection trajectoire."""
    response = authed_client_helios.get("/api/cockpit/trajectory")
    proj = response.json()["projection_mwh"]
    drops = [(proj[i+1] - proj[i]) / proj[i] for i in range(len(proj)-1) if proj[i] and proj[i+1]]
    assert all(d > -0.15 for d in drops), f"Drop trop violent détecté: {drops}"
```

**Commit** : `fix(cockpit-sol2): Phase 1.6 — trajectoire DT lissée par action.echeance (Q5)`

#### Phase 1.7 — Endpoint facture portefeuille (Q2)

```python
# backend/routes/purchase_cost_simulation.py

@router.get("/api/purchase/cost-simulation/portfolio/{org_id}")
async def cost_simulation_portfolio(org_id: int, db: Session = Depends(get_db)):
    """Agrège les simulations de coût des sites d'un org pour la Vue Exé."""
    sites = db.query(Site).filter(Site.org_id == org_id).all()
    site_simulations = [cost_simulation_for_site(site.id, db) for site in sites]
    return {
        "scope": {"org_id": org_id, "site_count": len(sites), "total_mwh_year": sum(s.volume_mwh for s in sites)},
        "total_eur": sum(sim["total_eur"] for sim in site_simulations),
        "components": aggregate_components(site_simulations),
        "post_arenh": True,
        "vs_2024_pct": -22.5,
    }
```

Le composant front « Facture énergie prévisionnelle » de la Vue Exé appelle désormais cet endpoint avec `org_id` au lieu de `/api/purchase/cost-simulation/1`.

**Source-guard** : `test_facture_portfolio_aggregation`
```python
def test_facture_portfolio_aggregation(authed_client_helios):
    response = authed_client_helios.get("/api/purchase/cost-simulation/portfolio/1")
    body = response.json()
    assert body["scope"]["site_count"] == 5
    assert body["scope"]["total_mwh_year"] == pytest.approx(4229, rel=0.01)
    assert body["total_eur"] > 500_000  # ~562 k€
```

**Commit** : `feat(cockpit-sol2): Phase 1.7 — endpoint facture cost-simulation portfolio (Q2)`

#### Phase 1.8 — Dictionnaire `acronym_to_narrative.py` (Q6)

```python
# backend/doctrine/acronyms.py

ACRONYM_TO_NARRATIVE = {
    "DT": "Décret Tertiaire",
    "BACS": "Décret BACS · pilotage CVC obligatoire",
    "GTB": "système de pilotage CVC",
    "TURPE": "tarif d'acheminement réseau",
    "APER": "obligation solaire parking",
    "OPERAT": "déclaration énergie tertiaire annuelle",
    "CDC": "courbe de charge 30 min",
    "VNU": "Versement Nucléaire Universel",
    "CBAM": "taxe carbone aux frontières",
    "ARENH": "ancien tarif réglementé (fin du dispositif)",
    "CEE": "Certificat d'économie d'énergie",
    "EPEX": "bourse électricité spot",
}

def transform_acronym(text: str, *, mode: str = "narrative") -> str:
    """Transforme acronymes bruts en récit selon doctrine §6.4.
    mode='narrative' : remplace par récit complet
    mode='inline' : garde acronyme + récit entre parenthèses la 1re fois
    """
```

Front consomme via mixin React `useAcronymTransformer()` :
```jsx
const { transform } = useAcronymTransformer();
<h3>{transform("Décret BACS")}</h3>
```

**Source-guard** : `test_acronyms_transformed_vue_executive`
```python
def test_acronyms_transformed_vue_executive(authed_client):
    """Aucun acronyme brut en titre de card Vue Exé."""
    response = authed_client.get("/api/pages/cockpit_comex/briefing")
    body = response.json()
    forbidden_in_titles = ["DT", "BACS", "GTB", "TURPE", "APER", "VNU", "CBAM", "ARENH"]
    for card in body.get("cards", []):
        title = card.get("title", "")
        for acr in forbidden_in_titles:
            assert not re.search(rf"\b{acr}\b", title), f"Acronyme brut '{acr}' dans titre: {title}"
```

**Commit** : `feat(cockpit-sol2): Phase 1.8 — dictionnaire acronyme→récit centralisé (Q6)`

#### Phase 1.9 — Seed `created_at` réparti (Q7)

Modifier les seeds notifications dans `gen_*.py` pour répartir `created_at` :

```python
# backend/services/demo_seed/gen_notifications.py

NOTIFICATION_SCHEDULE = [
    {"label": "Action 'Renouveler contrat Paris'", "hours_ago": 3},
    {"label": "DT BACS Nice : inspection programmée", "hours_ago": 28},  # hier
    {"label": "DT APER Toulouse : étude solaire", "hours_ago": 52},  # avant-hier
    {"label": "Anomalie weekend Marseille", "hours_ago": 96},  # 4 jours
]
```

**Source-guard** : `test_notifications_timestamps_distributed`
```python
def test_notifications_timestamps_distributed(authed_client_helios):
    response = authed_client_helios.get("/api/notifications/list?limit=4")
    timestamps = [n["created_at"] for n in response.json()["items"]]
    diffs_hours = [(now - t).total_seconds() / 3600 for t in timestamps]
    # Au moins 3 échelles temporelles différentes (heures / jour / jours)
    assert len(set([floor_hours(d) for d in diffs_hours])) >= 3
```

**Commit** : `fix(cockpit-sol2): Phase 1.9 — seed created_at réparti sur 7 jours (Q7)`

### 2.C — Definition of Done Phase 1

- [ ] Modèle `EurAmount` + service traçabilité livré
- [ ] Service `baseline_service` avec 3 méthodes A/B/C livré
- [ ] Modèle `BaselineCalibration` + job re-calibration + seed HELIOS DJU 12 mois livrés
- [ ] Endpoint atomique `_facts` livré, consommé par `briefing_daily` et `briefing_comex`
- [ ] 5 fichiers `models/*.js` migrés en backend Python
- [ ] Surface HELIOS = 17 500 m² (vs 35 000 actuel)
- [ ] Trajectoire DT lissée (drop YoY < 15 %)
- [ ] Endpoint `cost-simulation/portfolio/{org_id}` livré
- [ ] Dictionnaire acronymes + mixin React livrés
- [ ] Notifications `created_at` réparties
- [ ] Source-guards créés et verts :
  - `test_eur_amount_typed`, `test_eur_amount_traceability`, `test_no_modeled_eur_amount`
  - `test_baseline_method_documented`, `test_baseline_r_squared_threshold`, `test_no_baseline_computation_in_frontend`, `test_baseline_a_fallback`
  - `test_cockpit_facts_unique_source`, `test_cockpit_facts_no_recompute`, `test_cockpit_facts_dt_penalty_doctrine`
  - `test_no_business_logic_in_frontend_cockpit`
  - `test_helios_surface_total`
  - `test_trajectory_smoothed_by_echeance`
  - `test_facture_portfolio_aggregation`
  - `test_acronyms_transformed_vue_executive`
  - `test_notifications_timestamps_distributed`
- [ ] Tests baseline 5 861 BE + 4 237 FE maintenus
- [ ] 9 commits atomiques Phase 1.1 à 1.9

---

## 3. Phase 2 — Chiffrage doctrinal (semaine 5)

### 3.A — Objectif

Re-typer tous les chiffres € exposés selon doctrine traçabilité (catégorie A réglementaire ou B contractuelle). Convertir en énergie tout ce qui ne passe pas le filtre.

### 3.B — Backlog atomique

#### Phase 2.1 — KPI Leviers € → MWh/an (Q1)

Modifier `narrative_generator.build_cockpit_comex_briefing` :

```python
# AVANT
LEVIER_ESTIME_PAR_SITE_EUR = 8500.0  # heuristique modélisée, à remplacer S5
leviers_estimes_eur = max(0, en_derive * LEVIER_ESTIME_PAR_SITE_EUR)

# APRÈS
from backend.routes.cockpit import _compute_savings_kwh
savings_kwh = _compute_savings_kwh(actions_open, scope)
levers_kpi = {
    "value_mwh_year": round(savings_kwh / 1000, 0),  # ex: 245
    "method": "modeled_cee",
    "references": ["CEE BAT-TH-116", "CEE BAT-TH-104"],
    "leverage_count": len(actions_open),
}
```

Sur la maquette : KPI 3 affiche « 245 MWh/an » avec badge `Modélisé · CEE BAT-TH-116 · 3 leviers `.

**Source-guard** : `test_levers_kpi_in_mwh_not_eur`
```python
def test_levers_kpi_in_mwh_not_eur(authed_client_helios):
    response = authed_client_helios.get("/api/pages/cockpit_comex/briefing")
    levers_kpi = next(k for k in response.json()["kpis"] if k["id"] == "levers")
    assert "value_mwh_year" in levers_kpi
    assert "value_eur" not in levers_kpi  # interdit
```

**Commit** : `feat(cockpit-sol2): Phase 2.1 — KPI Leviers exposé en MWh/an (Q1, décision A)`

#### Phase 2.2 — KPI Exposition décomposé loi à la main

Le KPI Exposition 26,2 k€ doit afficher dans son tooltip la décomposition complète article par article :

```
26,2 k€ exposition réglementaire
├─ 1 site non conforme × 7 500 € (Décret 2019-771 art. 9) = 7 500 €
├─ 4 sites à risque × 3 750 € (Décret 2019-771 art. 9 al. 2) = 15 000 €
├─ 1 site BACS non conforme × 1 500 € (Décret 2020-887) = 1 500 €
└─ 1 déclaration OPERAT manquante × 1 500 € (Circulaire DGEC 2024) = 1 500 €
                                                          Total = 25 500 € + 700 € arrondi = 26,2 k€
```

Code : `narrative_generator.py` importe `DT_PENALTY_EUR=7500`, `DT_PENALTY_AT_RISK_EUR=3750`, `BACS_PENALTY_EUR=1500`, `OPERAT_PENALTY_EUR=1500` depuis `doctrine/constants.py` (les ajouter si manquants).

**Source-guards** :
- `test_exposure_kpi_decomposed` — la réponse API de l'exposition contient un champ `components` avec 4 entrées chacune dotée de `regulatory_article`
- `test_dt_penalty_uses_doctrine_constants` — `narrative_generator.py` n'a aucune occurrence littérale `7500.0`, importe `DT_PENALTY_EUR`

**Commit** : `feat(cockpit-sol2): Phase 2.2 — KPI Exposition décomposé loi à la main + constantes doctrine`

#### Phase 2.3 — Top 3 actions : impact en MWh/an

Pour chaque action de la file Top 3 affichée Vue Exé :

```python
# backend/services/action_hub_service.py

def serialize_action_for_decision(action: ActionItem) -> dict:
    return {
        "id": action.id,
        "title": transform_acronym(action.title),  # ex: "Installer un système de pilotage CVC (GTB classe A/B)"
        "narrative": action.narrative,
        "site": action.site.name,
        "echeance": action.echeance.isoformat(),
        # AVANT: "estimated_gain_eur": 15000
        # APRÈS:
        "estimated_gain_mwh_year": round(action.estimated_gain_eur / DEFAULT_PRICE_ELEC_EUR_KWH / 1000),
        "reference": action.cee_reference or action.regulatory_article,  # ex: "CEE BAT-TH-116"
        # Si action a impact pénalité légale (action de mise en conformité):
        "regulatory_penalty_eur": EurAmount.regulatory(action.penalty_eur, article=action.regulatory_article).to_dict() if action.penalty_eur else None,
    }
```

Sur la maquette Décision 1 : « Économies modélisées 115 MWh/an · CEE BAT-TH-116 » + « pénalité légale 7 500 €/an · Décret 2019-771 art. 9 ».

**Source-guard** : `test_actions_decision_show_mwh_or_traced_eur`
```python
def test_actions_decision_show_mwh_or_traced_eur(authed_client_helios):
    response = authed_client_helios.get("/api/cockpit/decisions/top3")
    for action in response.json()["actions"]:
        # Soit MWh exposé, soit € avec traceability
        has_mwh = "estimated_gain_mwh_year" in action
        eur_traced = action.get("regulatory_penalty_eur", {}).get("regulatory_article") is not None
        assert has_mwh or eur_traced
```

**Commit** : `feat(cockpit-sol2): Phase 2.3 — top 3 actions impact MWh/an + traçabilité euros`

#### Phase 2.4 — Footer file actions « 245 MWh/an récupérables »

Remplacer « Actions planifiées · Économie potentielle : 128 k€/an » par :

```
Actions planifiées · Potentiel énergétique : 245 MWh/an récupérables
Modélisé · 11 actions ouvertes · références CEE BAT-TH-116, BAT-TH-104, BAT-TH-115
```

**Commit** : `feat(cockpit-sol2): Phase 2.4 — footer file actions en MWh/an`

### 3.C — Definition of Done Phase 2

- [ ] KPI Leviers exposé en MWh/an, plus aucun `LEVIER_ESTIME_PAR_SITE_EUR` heuristique
- [ ] KPI Exposition décomposé en composants article par article via tooltip
- [ ] Top 3 actions Décision affichent impact MWh/an + pénalité € traçable si applicable
- [ ] Footer file actions en MWh/an
- [ ] Constantes doctrine `DT_PENALTY_EUR`, `BACS_PENALTY_EUR`, `OPERAT_PENALTY_EUR` toutes utilisées (zéro littéral)
- [ ] Source-guards créés et verts :
  - `test_levers_kpi_in_mwh_not_eur`
  - `test_exposure_kpi_decomposed`
  - `test_dt_penalty_uses_doctrine_constants`
  - `test_actions_decision_show_mwh_or_traced_eur`
- [ ] Tests baseline maintenus
- [ ] 4 commits atomiques

---

## 4. Phase 3 — Réciprocité Décision ⇄ Pilotage (semaine 6)

### 4.A — Objectif

Tisser les liens bidirectionnels entre les 2 vues. Switch éditorial intégré au kicker. Push événementiel hebdo.

### 4.B — Backlog atomique

#### Phase 3.1 — Switch éditorial dans le kicker

```jsx
// frontend/src/pages/cockpit/CockpitModeSwitch.jsx
<div className="cockpit-kicker-switch">
  <a href="/cockpit/jour" className={mode === 'jour' ? 'active' : ''}>Briefing du jour</a>
  <span>⇄</span>
  <a href="/cockpit/strategique" className={mode === 'strategique' ? 'active' : ''}>Synthèse stratégique</a>
</div>
```

Routes :
- `/cockpit/jour` → page Pilotage (ex `CommandCenter.jsx` renommé `CockpitDaily.jsx`)
- `/cockpit/strategique` → page Décision (ex `Cockpit.jsx` renommé `CockpitStrategic.jsx`)
- `/cockpit` → redirect vers `/cockpit/jour` (default mode)
- `/dashboard`, `/executive`, `/synthese` → redirect 410 Gone avec log

**Default mode intelligent** (chantier γ) :
- Si rôle utilisateur ∈ {DG, CFO, Propriétaire} → default `/cockpit/strategique`
- Sinon → default `/cockpit/jour`
- Stocker préférence utilisateur dans localStorage après 1ʳᵉ visite

**Commit** : `feat(cockpit-sol2): Phase 3.1 — switch éditorial dans kicker + routes /cockpit/jour | /strategique`

#### Phase 3.2 — Drill-downs KPI hero (Q8)

Sur la Décision, chaque KPI hero a un drill-down explicite :

| KPI | Cible drill-down | Contexte préservé |
|---|---|---|
| Trajectoire 2030 | `/conformite?scope=org&filter=non_conform` | scope HELIOS + 3 sites en dérive |
| Exposition 26,2 k€ | `/conformite?scope=org&view=exposure_components` | tableau décomposition art par art |
| Potentiel 245 MWh/an | `/actions?filter=open&sort=mwh_desc` | 11 actions triées par impact MWh décroissant |

Sur le Pilotage, chaque ligne P1-P3 critique a un lien « voir impact stratégique ↗ » :
- Ouvre `/cockpit/strategique#decision-{id}` qui scroll vers la décision correspondante
- Si la dérive opérationnelle n'a pas encore de décision liée, créer une décision draft à la volée

**Source-guards** :
- `test_kpi_hero_has_drill_down` — chaque KPI hero a un href cible documenté
- `test_pilotage_action_has_decision_link` — chaque action critique (P1-P2) a un lien vers Décision

**Commit** : `feat(cockpit-sol2): Phase 3.2 — drill-downs KPI hero + liens action → décision (Q8)`

#### Phase 3.3 — Push événementiel « +X vs S-1 »

Backend : ajouter `_compute_weekly_delta` dans `cockpit_facts_service.py` :

```python
def compute_weekly_delta(metric_name: str, scope: dict, current_week: date) -> dict:
    """Calcule l'évolution d'une métrique semaine vs semaine précédente."""
    current = get_metric(metric_name, scope, week=current_week)
    previous = get_metric(metric_name, scope, week=current_week - timedelta(days=7))
    return {
        "current": current,
        "previous": previous,
        "delta_absolute": current - previous,
        "delta_pct": (current - previous) / previous if previous else None,
        "direction": "up" if current > previous else "down" if current < previous else "stable",
    }
```

Métriques avec push hebdo :
- Exposition réglementaire (« +3,8 k€ vs S-1 »)
- Potentiel récupérable (« +18 MWh/an vs S-1 »)
- Sites en dérive (« +1 site vs S-1 »)
- Score conformité (« stable / -2 pts vs S-1 »)

Front : narrative Vue Exé intègre ces deltas explicitement.

**Source-guard** : `test_vue_executive_pushes_weekly_evolution`

**Commit** : `feat(cockpit-sol2): Phase 3.3 — push événementiel +X vs S-1 sur 4 métriques (doctrine §11.3 push hebdo)`

#### Phase 3.4 — Suppression routes legacy

```python
# backend/routes/legacy_redirects.py
@router.get("/dashboard", "/executive", "/synthese", "/tableau-de-bord")
async def legacy_redirect(request: Request):
    log_legacy_access(request.url.path)
    if get_user_role(request) in {"DG", "CFO"}:
        return RedirectResponse("/cockpit/strategique", status_code=410)
    return RedirectResponse("/cockpit/jour", status_code=410)
```

**Source-guard** : `test_no_route_legacy_executive`

**Commit** : `feat(cockpit-sol2): Phase 3.4 — routes legacy redirect 410 + log`

### 4.C — Definition of Done Phase 3

- [ ] Switch éditorial fonctionnel dans le kicker
- [ ] Routes `/cockpit/jour` + `/cockpit/strategique` actives
- [ ] Routes legacy redirect 410 avec log
- [ ] Default mode intelligent selon rôle
- [ ] 3 drill-downs KPI hero Décision livrés
- [ ] Liens « voir impact stratégique ↗ » sur P1-P2 Pilotage
- [ ] Push hebdo sur 4 métriques (Exposition, Potentiel, Sites, Score)
- [ ] Source-guards créés et verts :
  - `test_kpi_hero_has_drill_down`
  - `test_pilotage_action_has_decision_link`
  - `test_vue_executive_pushes_weekly_evolution`
  - `test_no_route_legacy_executive`
- [ ] 4 commits atomiques

---

## 5. Phase 4 — Validation utilisateur réelle (semaine 7)

### 5.A — Objectif

Test doctrinal §11.3 DoD : « Vue Exécutive comprise en 3 min par dirigeant non-sachant + Tableau de bord utile en 30 s par energy manager ». **Ce n'est pas un test pytest.** C'est un test sur des humains réels.

### 5.B — Protocole de test

#### Phase 4.1 — Recrutement panel

- 2 dirigeants tertiaires non-sachants énergie (CFO ETI ou DG ETI) — réseau Promeos Amine
- 2 energy managers (responsables exploitation patrimoine) — réseau professionnel
- Profils : tertiaire mid-market, 5-30 sites, jamais utilisé Promeos
- Rémunération de la session : à arbitrer (ex: 100 € chacun, 1h)

#### Phase 4.2 — Test Vue Exécutive (3 min chronométrés)

Protocole strict :
1. Dirigeant arrive en salle
2. Présentation neutre : « Je vais vous montrer une page web pendant 3 minutes. Vous prenez le temps de la lire silencieusement. »
3. Affichage Vue Exécutive scope HELIOS (capture statique pour éviter clics)
4. Chronomètre 3 min, aucune intervention
5. À la fin : « En 30 secondes, dites-moi ce que vous avez compris de la situation de cette entreprise. »
6. Enregistrer la réponse mot pour mot

**Critères de réussite (chacun doit être identifié spontanément) :**
- ✅ Le patrimoine de 5 sites a un risque réglementaire
- ✅ Il y a un score (37/100) en deçà de la cible 2030
- ✅ Il y a une exposition financière (~26 k€)
- ✅ Il y a 3 décisions à arbitrer cette semaine
- ✅ Il y a un potentiel énergétique récupérable (245 MWh/an)

**Critères bonus (souhaitables mais non bloquants) :**
- L'audit énergétique est obligatoire avant le 11 octobre
- La trajectoire 2030 reste atteignable avec les actions planifiées
- Il y a un gisement Flex de 21 k€/an

**Validation** : si 2/2 dirigeants identifient les 5 critères principaux en 3 min → DoD validé.

#### Phase 4.3 — Test Tableau de bord (30 s chronométrés)

Protocole identique avec :
- Energy manager au lieu de dirigeant
- 30 s chronométrées au lieu de 3 min
- Question : « Qu'est-ce que vous traiteriez en priorité aujourd'hui ? »

**Critères de réussite :**
- ✅ Identifier au moins 2 lignes de la file de traitement comme prioritaires
- ✅ Identifier qu'il y a une anomalie sur l'Hôtel Nice
- ✅ Identifier la dérive de puissance souscrite Toulouse
- ✅ Comprendre que la conso de J-1 est anormalement haute

#### Phase 4.4 — Itération sur retours

Pour chaque critère non atteint :
- Documenter dans `docs/sprints/SPRINT_COCKPIT_DUAL_SOL2.md` quel critère a échoué et pourquoi
- Identifier le composant concerné
- Mini-Sprint correctif (1-3 j) avant validation finale

**Commits** : commits selon corrections nécessaires, format `fix(cockpit-sol2): Phase 4.4 — correction X suite test utilisateur Y`

### 5.C — Definition of Done Phase 4

- [ ] 2 dirigeants testés Vue Exécutive 3 min
- [ ] 2 energy managers testés Tableau de bord 30 s
- [ ] Compte-rendu des 4 sessions documenté dans `docs/sprints/`
- [ ] 100 % des critères principaux identifiés (sinon mini-sprint correctif)
- [ ] Tests baseline maintenus

---

## 6. Phase 5 — Mesure & itération continue (semaines 7+)

### 6.A — Objectif

Mettre en place les mécanismes de mesure permanente pour que la doctrine ne dérive pas une fois en production.

### 6.B — Backlog atomique

#### Phase 5.1 — Capture Playwright J vs J+1 hebdo

Cron job hebdo :
```bash
node tools/playwright/capture-cockpit-weekly.mjs --output=docs/captures/$(date +%Y-W%U)/
```

Output : screenshot Vue Exécutive + Tableau de bord, avec hash SHA-256. Si hash identique J vs J+7 sur ≥ 5 zones → alerte « page figée, push événementiel ne fonctionne plus ».

#### Phase 5.2 — Mesure performance réseau

CI metric : capture nombre de requêtes API au mount Vue Exé et Tableau de bord. Objectif : < 50 requêtes (vs 131 actuel).

```python
# backend/tests/test_perf_cockpit.py
def test_cockpit_request_count_under_50(playwright_session):
    requests = playwright_session.capture_network("/cockpit/strategique")
    assert len(requests) < 50, f"Trop de requêtes: {len(requests)}"
```

#### Phase 5.3 — Analytics drill-downs

Backend logging :
- Chaque clic drill-down KPI hero → log `analytics_drill_down`
- Chaque switch Pilotage ↔ Décision → log `analytics_mode_switch`
- Hebdo : dashboard interne « top 3 KPI cliqués », « top 3 actions ouvertes », « rate switch jour ↔ stratégique »

#### Phase 5.4 — Doctrine review trimestrielle

Tous les 3 mois, agenda :
- Re-test 3 min / 30 s sur 2 nouveaux utilisateurs
- Audit visuel : aucune card ajoutée sans justification doctrinale
- Audit copy : aucun acronyme brut introduit
- Audit chiffrage : aucun € sans traçabilité réglementaire/contractuelle

### 6.C — Definition of Done Phase 5

- [ ] Cron Playwright J vs J+1 actif
- [ ] CI metric perf réseau < 50 requêtes
- [ ] Logging analytics drill-downs actif
- [ ] Doctrine review Q3 2026 planifiée

---

## 7. Definition of Done Sprint global

- [ ] Phases 0 à 5 complétées
- [ ] ~50 source-guards pytest verts en CI
- [ ] Tests baseline 5 861 BE + 4 237 FE maintenus tout au long
- [ ] 8 DoD doctrinales §11.3 validées par test utilisateur réel
- [ ] Maquettes cibles `cockpit_pilotage_final_sol2_phase2` et `cockpit_decision_final_sol2_phase2` matérialisées en production
- [ ] Performance : < 50 requêtes API au mount par vue
- [ ] Densité : ≤ 7 blocs visibles à l'ouverture par vue
- [ ] Doctrine compliance documentée dans PR finale (principes 1-12 cochés)
- [ ] Commit final tag `cockpit-dual-sol2-v1.0`

---

## 8. Ce qui n'est PAS dans ce sprint (à acter explicitement)

- **Refonte Tableau de bord standalone** : ce sprint refond Tableau de bord ET Vue Exécutive ensemble pour garantir source unique. Pas de sprint séparé.
- **Module Flex Intelligence dédié** : la page Flex existe ou doit être créée (hors-périmètre Cockpit). Ce sprint Cockpit en consomme un teaser uniquement.
- **EMS Tier 2** (carpet plot, énergie signature, CUSUM, ML anomalies) : sprint séparé EMS.
- **Sprint A org-scoping P0** : Cockpit traite uniquement le leak Hypermarché Montreuil (slug hardcodé). Le reste du Sprint A (35 fichiers SQL filter) est un sprint sécurité distinct.
- **Mode mobile responsive** : priorité 2 du sprint suivant.
- **Internationalisation** : tout reste en français pour l'instant.
- **Test utilisateur > 5 personnes** : Phase 4 vise 4 personnes minimum. Études quantitatives plus larges = sprint UX research séparé.

---

## 9. Risques identifiés et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Migration `models/*.js` déborde Phase 1 | Moyenne | Élevé | Splitter en 5 sous-phases si > 3 j en sous-phase 1.4 |
| Recrutement panel test utilisateur Phase 4 | Élevée | Moyen | Démarrer le recrutement Phase 0 (semaine 1) en parallèle |
| Décisions Q4 surface bâtiment SHON vs utile | Faible | Moyen | Décision rapide après audit `SELECT site_id, COUNT(*)` |
| Endpoint `_facts` casse rétro-compatibilité | Moyenne | Élevé | Maintenir `briefing_daily` et `briefing_comex` pour compat 30 j puis dépréciation |
| Performance < 50 req difficile à atteindre | Moyenne | Moyen | Tolérance acceptée jusqu'à 70 req si baseline était 131 |
| Refus seed contrats fictifs HELIOS | Faible | Moyen | Si refus, tous les € de la Vue Exé passent en MWh (catégorie A uniquement, pas de B en démo) |

---

## 10. Convention de fin de sprint

À la fin du sprint :

1. PR finale avec le tag `cockpit-dual-sol2-v1.0`
2. Compte-rendu détaillé par phase dans `docs/sprints/SPRINT_COCKPIT_DUAL_SOL2.md`
3. Captures Playwright avant/après dans `docs/captures/cockpit-dual-sol2-before-after/`
4. Diapositive de présentation pour le board (si applicable) avec 8 DoD validées
5. Plan de déploiement progressif (10 % users → 50 % → 100 %) avec rollback plan
6. Sprint retro Amine ↔ Claude Code : qu'est-ce qui a marché, qu'est-ce qui a buggé, ajustements pour Sprint Tableau de bord refonte similaire

---

**Sprint Refonte Cockpit Dual Sol2 — exécution — méthodologie PROMEOS doctrine v1.0 §11.3 + arbitrages Amine 2026-04-28**

**À chaque fin de phase** : code-review MCP + simplify MCP obligatoires avant commit. Si l'un signale problème → ne pas committer, signaler à Amine, ajuster.

**À chaque fin de sprint** : ajustement collectif si nécessaire, puis sprint suivant (Refonte Conformité, Refonte Patrimoine, etc.).
