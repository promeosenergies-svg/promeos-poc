# ADR-023 — Synthèse stratégique data-driven

**Status** : `Proposed`
**Date** : 2026-05-13
**Author** : Amine + Claude (session refonte Synthèse v6→v8)
**Supersedes** : —
**Related** : ADR-022 (priorisation v1.0), ADR-024 (moteur assujettissement)

---

## Context

La page **Synthèse stratégique** (`/cockpit/strategique`) est la **deuxième page hub canonique** de PROMEOS après Briefing du Jour. Elle s'adresse au **persona DG/COMEX** avec un horizon **1-5 ans**, une **granularité portefeuille/groupe**, et une **fréquence hebdomadaire/mensuelle**.

Six itérations de design (v3→v8) ont convergé sur les principes suivants :

1. **Loi L11** stricte : 1 hero + exactement 3 KPIs + exactement 2 charts + 3-5 highlights + footer
2. **Patrimoine = point de départ** : `patrimoine → règles applicables → KPIs → alertes → actions → preuves`
3. **Polymorphisme** : la page change selon le `strategic_mode` calculé backend (cf. ADR-024)
4. **Backend authoritative** : aucun calcul métier dans le frontend, aucun statut réglementaire en dur
5. **Couches opérationnelles** : workflow de gouvernance numéroté, comparateur de scénarios, mini-timeline, score décision

Cette ADR cadre l'**architecture data-driven** qui matérialise ces principes.

---

## Decision

### 1. Endpoint orchestrateur unique

```python
# backend/routes/cockpit_strategique.py

@router.get("/cockpit/strategique")
def get_cockpit_strategique(
    request: Request,
    period_type: str = "month",          # défaut month (vs week pour briefing)
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    persona: str = "dg_comex",            # défaut DG/COMEX
    horizon_year: int = 2030,             # projection trajectoire
    portfolio_id: Optional[int] = None,   # filtre portefeuille optionnel
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> dict:
    org_id = resolve_org_id(request, auth, db)

    # 1. Évaluer le cadre applicable (ADR-024)
    applicability = compute_applicability(db, org_id)
    strategic_mode = compute_strategic_mode(db, org_id, applicability)
    patrimoine_maturity = compute_patrimoine_maturity(db, org_id)

    # 2. Router vers le bon builder
    builder = MODE_BUILDERS[strategic_mode]

    # 3. Construire la réponse polymorphique
    return builder.build(
        db=db,
        org_id=org_id,
        period=period,
        persona=Persona(persona),
        applicability=applicability,
        patrimoine_maturity=patrimoine_maturity,
        horizon_year=horizon_year,
    )
```

### 2. Cinq builders de mode

Chaque mode implémente le contrat `StrategicModeBuilder` :

```python
# backend/services/strategique/builders/base.py

class StrategicModeBuilder(ABC):
    mode: StrategicMode

    @abstractmethod
    def build(
        self,
        db: Session,
        org_id: int,
        period: dict,
        persona: Persona,
        applicability: dict[str, list[RuleApplicability]],
        patrimoine_maturity: float,
        horizon_year: int,
    ) -> dict:
        """Retourne le payload complet de la page Synthèse stratégique."""

    def _build_hero(...) -> dict: ...
    def _build_kpis(...) -> list[dict]: ...
    def _build_charts(...) -> list[dict]: ...
    def _build_dossier_p1(...) -> dict: ...
    def _build_queue_p2_p3(...) -> list[dict]: ...
    def _build_verdict(...) -> dict: ...
    def _build_footer(...) -> dict: ...


MODE_BUILDERS: dict[StrategicMode, StrategicModeBuilder] = {
    StrategicMode.REGULATORY_DRIVEN:  RegulatoryDrivenBuilder(),
    StrategicMode.PERFORMANCE_DRIVEN: PerformanceDrivenBuilder(),
    StrategicMode.PROCUREMENT_DRIVEN: ProcurementDrivenBuilder(),
    StrategicMode.OPPORTUNITY_DRIVEN: OpportunityDrivenBuilder(),
    StrategicMode.DATA_INSUFFICIENT: DataInsufficientBuilder(),
}
```

### 3. Contrat de réponse — schéma canonique

```json
{
  "strategic_mode": "performance_driven",
  "applicability": {
    "DT":    [{ "status": "not_applicable", "reason_human": "...", ... }],
    "BACS":  [{ "status": "not_applicable", "reason_human": "...", ... }],
    "APER":  [{ "status": "data_missing",   "reason_human": "...", ... }],
    "SME":   [{ "status": "applicable",     "reason_human": "...", ... }],
    "BEGES": [{ "status": "not_applicable", "reason_human": "...", ... }]
  },
  "patrimoine_maturity": 0.71,
  "verdict": {
    "constraint": {
      "label": "Votre contrainte principale",
      "statement": "n'est pas réglementaire, elle est économique.",
      "detail": "Aucune trajectoire DT ni BACS à tenir. Le levier majeur..."
    },
    "opportunity": {
      "label": "Votre opportunité principale",
      "statement": "est l'audit SMÉ couplé au pilotage, payback 1,4 an.",
      "detail": "L'audit étant déjà obligatoire avant le 11/10/2026..."
    }
  },
  "hero": {
    "kicker": "RECOMMANDATION PROMEOS · Synthèse stratégique · mai 2026",
    "title": "Performance énergétique sous la médiane sectorielle.",
    "title_em": "3 leviers d'économie à activer cette année.",
    "sub_constat": "Site Toulouse 22 % au-dessus du benchmark NAF...",
    "sub_implications": "Contrat élec à 156 €/MWh au-dessus de la médiane...",
    "meta": { "quality_pct": 88, "confidence": "haute", "period": "Mai 2026", ... },
    "ctas": [
      { "label": "Arbitrer les leviers", "verb": "arbitrer", "primary": true },
      { "label": "Brief COMEX (PDF)", "verb": "exporter" },
      { "label": "Simuler un scénario", "verb": "simuler" }
    ],
    "score": { "value": 76, "max": 100, "axes": ["impact","urgence","confiance","reversibilite"] }
  },
  "kpis": [
    {
      "id": "intensite_kwh_m2",
      "eyebrow": "Intensité énergétique",
      "value": 198, "unit": "kWh<sub>EF</sub>/m²",
      "delta": { "label": "+22 % vs médiane", "tier": "warn" },
      "context": "Site Toulouse tire l'intensité groupe à la hausse...",
      "tier": "warn",
      "trace_tag": "measure",
      "trace": { "source": "...", "formula": "...", "scope": "...", "freshness": "..." },
      "link": { "label": "Conso →", "route": "/conso" }
    }
    /* + 2 autres KPIs */
  ],
  "charts": [
    {
      "id": "bench_sites_intensity",
      "type": "bench_sites",
      "question": "Quels sites tirent la performance vers le bas ?",
      "answer": "Toulouse +22 % au-dessus de la médiane. Nantes -18 % meilleur élève — réplicabilité à étudier.",
      "data": [
        { "site": "Toulouse", "value": 198, "ref": 162, "delta_pct": 22, "tier": "warn" },
        { "site": "Bordeaux", "value": 168, "ref": 162, "delta_pct": 4, "tier": "neutral" },
        { "site": "Nantes",   "value": 133, "ref": 162, "delta_pct": -18, "tier": "pos" }
      ],
      "foot_scm": "Source · INSEE NAF C28.99 · 12 mois glissants · 3 sites MERIDIAN"
    }
    /* + 1 autre chart */
  ],
  "dossier_p1": {
    "priority": "P1",
    "urgency_label": "J-155",
    "category": "FINANCIER",
    "question": "Comment ramener Toulouse au niveau de Nantes ?",
    "recommendation": "Lancer un audit énergétique SMÉ Toulouse + plan de pilotage CTA, finançable sur 12 mois.",
    "proof_pills": [
      { "axis": "gravite", "tier": "warn", "value": "Perte récurrente" },
      { "axis": "impact",  "tier": "warn", "value": "320 MWh/an · 49 k€/an" },
      { "axis": "delai",   "tier": "warn", "value": "J-155 (SMÉ)" },
      { "axis": "confiance", "tier": "ok", "value": "Haute" },
      { "axis": "reversibilite", "tier": "neutral", "value": "Élevée" }
    ],
    "body_html": "<p>Le site Toulouse...</p>",
    "scenarios": [
      { "label": "A · Reporter", "title": "Audit SMÉ minimal seul", "figs": {...}, "verdict": "..." },
      { "label": "B · Recommandé", "title": "Audit SMÉ + plan pilotage CTA", "figs": {...}, "recommended": true },
      { "label": "C · Alternative", "title": "Rénovation lourde différée", "figs": {...} }
    ],
    "timeline": [
      { "step": "decision",     "name": "Décision",      "date": "Q3 2026", "status": "current" },
      { "step": "framework",    "name": "Cahier charges", "date": "Q4 2026", "status": "future" }
      /* ... */
    ],
    "proof_sidebar": [
      { "label": "CAPEX audit + CTA", "value": "68 k€", "detail": "Devis APAVE 2025" }
      /* ... */
    ],
    "why_promeos": "<p>Trois facteurs convergent...</p>",
    "links": ["/conso", "/centre-arbitrage"],
    "_audit": { ... }
  },
  "queue_p2_p3": [ /* 2-4 arbitrages secondaires */ ],
  "continuity": { "last_visit": "...", "items": [...] },
  "footer": {
    "sources": [...],
    "version_tags": ["Assujettissement v1.0", "Doctrine priorisation v1.0", "Sol v1.1"],
    "last_update": "12/05 07:18",
    "methodology_link": "/methodologie"
  }
}
```

### 4. Adaptation par mode — différences cardinales

| Section | REGULATORY | PERFORMANCE | PROCUREMENT | OPPORTUNITY | DATA_INSUFFICIENT |
|---|---|---|---|---|---|
| Hero title | "Trajectoire DT 2030 à X %" | "Performance sous médiane" | "Contrat à échéance, fenêtre Y+1" | "N opportunités · X k€/an" | "Cadre indéterminé · N infos" |
| KPI 1 | Trajectoire DT % | Intensité kWh/m² | Coût €/MWh forward | Potentiel PV k€/an | Maturité patrimoine % |
| KPI 2 | Coût €/MWh vs P50 | Coût €/MWh | Exposition spot % | CEE valorisables k€ | Sites qualifiés |
| KPI 3 | Reclaim k€ | Économies activables k€ | Économie scénario k€ | Flex k€/an | Données manquantes |
| Chart 1 | TrajectoryLine | BenchSites | ForwardCurve | OpportunityMap | MaturityRadar |
| Chart 2 | MixHorizontal | Pareto leviers | MixHorizontal cibles | ROI bars | MissingFields |
| Catégorie P1 | RÉGLEMENTAIRE | FINANCIER | FINANCIER | STRATÉGIQUE | PLATEFORME |
| CTAs verbes | arbitrer / simuler / contester | arbitrer / simuler / comparer | arbitrer / simuler / comparer | simuler / qualifier / comparer | renseigner / importer / qualifier |

### 5. Nouveaux primitifs frontend

Trois primitifs à créer dans `frontend/src/components/grammar/hub/` :

```jsx
// 1. <StrategicModeBanner /> — bandeau au-dessus du data banner
<StrategicModeBanner
  mode={payload.strategic_mode}
  rules={payload.applicability}
  onDrawerOpen={() => setApplicabilityDrawerOpen(true)}
/>

// 2. <CadreApplicable /> — bloc sous hero
<CadreApplicable
  rules={payload.applicability}
  maturity={payload.patrimoine_maturity}
  onRuleClick={(rule) => setRuleDetailDrawer(rule)}
  onSimulate={() => navigate('/patrimoine/simuler')}
/>

// 3. <VerdictFinal /> — bloc avant la file P2/P3
<VerdictFinal
  constraint={payload.verdict.constraint}
  opportunity={payload.verdict.opportunity}
/>
```

Deux primitifs chart à créer Phase 3.5 (2 autres en Phase 3.6) :

```jsx
// 4. <ChartFrameTrajectoryLine /> — REGULATORY_DRIVEN
// 5. <ChartFrameBenchSites /> — PERFORMANCE_DRIVEN
// (les autres : ForwardCurve, OpportunityMap, MaturityRadar, MissingFields en Phase 3.6)
```

### 6. Anti-patterns interdits

Compléments à la Loi L11 (doctrine §6.5) spécifiques à cette page :

| AP | Description | Interdit |
|---|---|---|
| **AP-stratX1** | Afficher une trajectoire DT/BACS si statut `UNKNOWN` ou `DATA_MISSING` | ❌ |
| **AP-stratX2** | Hardcode du `strategic_mode` dans la route ou un builder | ❌ |
| **AP-stratX3** | Builder qui appelle directement la DB pour évaluer une règle (doit passer par `regulatory_applicability_service`) | ❌ |
| **AP-stratX4** | Verdict final ("contrainte principale") en dur dans le frontend | ❌ |
| **AP-stratX5** | Plus de 5 highlights ou moins de 3 dans la file P2/P3 | ❌ |
| **AP-stratX6** | KPI sans `trace` complète (source, formula, scope, freshness) | ❌ |
| **AP-stratX7** | Référence à un nom de site/portefeuille spécifique dans un builder (doit venir de la DB) | ❌ |
| **AP-stratX8** | Workflow gouvernance sans owner + échéance + pièce + décision | ❌ |

### 7. Tests source-guards obligatoires

```python
# backend/tests/source_guards/test_strategique_data_driven.py

def test_no_hardcoded_strategic_mode(route_source: str):
    """Le mode doit toujours être calculé."""
    forbidden = [
        '"strategic_mode": "regulatory_driven"',
        '"strategic_mode": "performance_driven"',
        'StrategicMode.REGULATORY_DRIVEN  #',
    ]
    for p in forbidden:
        assert p not in route_source

def test_uses_compute_strategic_mode(route_source: str):
    assert "compute_strategic_mode" in route_source
    assert "compute_applicability" in route_source

def test_no_hardcoded_dt_trajectory_value(builder_sources: list[str]):
    """Aucune valeur 73, 47, -32, -40 en dur dans builders."""
    forbidden = ['"value": 73,', '"value": 47,', '-32 %', '-40 %']
    for src in builder_sources:
        for p in forbidden:
            assert p not in src

def test_builder_returns_required_keys(payload: dict):
    """Tout builder doit retourner ces clés cardinales."""
    required = ["strategic_mode", "applicability", "patrimoine_maturity",
                "verdict", "hero", "kpis", "charts", "dossier_p1",
                "queue_p2_p3", "continuity", "footer"]
    for k in required:
        assert k in payload, f"Missing key: {k}"

def test_kpis_have_complete_trace(payload: dict):
    """Chaque KPI doit avoir source/formula/scope/freshness."""
    for kpi in payload["kpis"]:
        assert "trace" in kpi
        for field in ["source", "formula", "scope", "freshness"]:
            assert field in kpi["trace"], f"KPI {kpi['id']} missing trace.{field}"

def test_data_insufficient_never_shows_dt_trajectory(payload: dict):
    """Si DATA_INSUFFICIENT, jamais de trajectoire DT en KPI 1."""
    if payload["strategic_mode"] == "data_insufficient":
        assert payload["kpis"][0]["id"] != "trajectoire_dt"
```

### 8. Page frontend — dispatcher de mode

```jsx
// frontend/src/pages/CockpitStrategique.jsx

export default function CockpitStrategique() {
  const { period } = useFilter();
  const { persona, setDataQualityPct } = usePersona();
  const [payload, setPayload] = useState(null);
  /* ... fetch standard ... */

  // La page ne fait JAMAIS de calcul de mode — elle lit payload.strategic_mode
  const mode = payload?.strategic_mode;

  return (
    <div data-page="cockpit-strategique" data-doctrine="L11" data-mode={mode}>
      <StrategicModeBanner mode={mode} rules={payload?.applicability} />

      <HubPage pillar="strategique">
        <SolHeroPremiumNight {...payload?.hero} />

        <CadreApplicable
          rules={payload?.applicability}
          maturity={payload?.patrimoine_maturity}
        />

        <HubPage.KpiTriptych>
          {payload?.kpis.map(k => <HubKpiCard key={k.id} {...k} />)}
        </HubPage.KpiTriptych>

        <HubPage.ChartPair>
          {payload?.charts.map(c => renderChartByType(c))}
        </HubPage.ChartPair>

        <DossierP1 {...payload?.dossier_p1} />

        <VerdictFinal {...payload?.verdict} />

        <QueueP2P3 items={payload?.queue_p2_p3} />

        <ContinuityStrip {...payload?.continuity} />

        <HubPageFooter {...payload?.footer} />
      </HubPage>
    </div>
  );
}
```

### 9. Définition des seuils trigger (référence)

```python
# backend/services/strategique/mode_thresholds.py

@dataclass(frozen=True)
class ModeThresholds:
    """Seuils versionnés v1.0 — modifiables uniquement par ADR."""

    # DATA_INSUFFICIENT (priorité 1, gate)
    MIN_PATRIMOINE_MATURITY: float = 0.60
    MAX_UNKNOWN_RULES_RATIO: float = 0.30

    # OPPORTUNITY_DRIVEN
    MIN_OPPORTUNITY_VALUE_K_EUR: float = 50.0  # k€/an cumulé pour basculer

    # PROCUREMENT_DRIVEN
    MAX_CONTRACT_END_DAYS: int = 90
    MAX_SPOT_EXPOSURE_PCT: float = 40.0

    # PERFORMANCE_DRIVEN (défaut si rien d'autre)
    MIN_BENCH_DEVIATION_PCT: float = 10.0

    # REGULATORY_DRIVEN (prime sur tout sauf DATA_INSUFFICIENT)
    MIN_TRAJECTORY_DRIFT_PCT: float = 5.0


def compute_strategic_mode(...) -> StrategicMode:
    t = ModeThresholds()

    # Gate 1 : DATA_INSUFFICIENT prime sur tout
    if maturity < t.MIN_PATRIMOINE_MATURITY:
        return StrategicMode.DATA_INSUFFICIENT
    unknown_ratio = sum(1 for r in all_rules if r.status == "unknown") / len(all_rules)
    if unknown_ratio > t.MAX_UNKNOWN_RULES_RATIO:
        return StrategicMode.DATA_INSUFFICIENT

    # Gate 2 : REGULATORY_DRIVEN si DT/BACS applicable + dérive
    has_dt_or_bacs_applicable = any(
        r.status == "applicable" for r in applicability.get("DT", []) + applicability.get("BACS", [])
    )
    if has_dt_or_bacs_applicable and trajectory_drift > t.MIN_TRAJECTORY_DRIFT_PCT:
        return StrategicMode.REGULATORY_DRIVEN

    # Gate 3 : PROCUREMENT_DRIVEN si contrat à échéance proche
    if next_contract_end_days < t.MAX_CONTRACT_END_DAYS or spot_exposure > t.MAX_SPOT_EXPOSURE_PCT:
        return StrategicMode.PROCUREMENT_DRIVEN

    # Gate 4 : OPPORTUNITY_DRIVEN si APER applicable ou CEE non valorisés
    has_aper_applicable = any(r.status == "applicable" for r in applicability.get("APER", []))
    if has_aper_applicable or unvalued_cee_k_eur > t.MIN_OPPORTUNITY_VALUE_K_EUR:
        return StrategicMode.OPPORTUNITY_DRIVEN

    # Défaut : PERFORMANCE_DRIVEN
    return StrategicMode.PERFORMANCE_DRIVEN
```

---

## Consequences

### Positives

1. **Polymorphisme cardinal** : 5 régimes narratifs, jamais de contenu hors sujet
2. **Patrimoine est le pivot** : la chaîne `patrimoine → règles → KPIs → arbitrages` est explicite et auditable
3. **Architecture extensible** : ajout d'un 6e mode (climate-driven, ETS2-driven) n'impacte que 1 builder + 1 trigger
4. **Source unique de vérité** : aucun calcul, aucun statut, aucun nom de site en dur côté frontend
5. **Différenciation produit forte** : aucun concurrent ne propose cette adaptation polymorphique

### Risques

1. **Complexité backend** : 5 builders × 7 sections × tests = ~25 j/h Phase 3.5
2. **Tests combinatoires** : 5 modes × N profils HELIOS/MERIDIAN/etc. → matrice de test à maintenir
3. **Évolution sémantique** : le langage "contrainte principale / opportunité principale" doit rester stable pour la mémoire utilisateur
4. **Frontend chart primitives** : 6 nouveaux chart types à implémenter → séquencer Phase 3.5 (2) + Phase 3.6 (4)

### Migration

Aucune. Cette page est nouvelle. Le commit de référence Briefing du Jour (`32916787` branche `claude/refonte-sol2`) sert de pattern à mirror, pas à modifier.

---

## Implementation plan

### Phase 3.5 — Sprint Synthèse stratégique (~22-25 j/h)

| # | Item | Effort |
|---|---|---|
| 1 | ADR-023 + ADR-024 actés et committés | 0.5 j/h |
| 2 | `regulatory/rules_catalog.py` + `applicability_service.py` (cf. ADR-024) | 5 j/h |
| 3 | `strategique/mode_thresholds.py` + `compute_strategic_mode` | 2 j/h |
| 4 | `strategique/builders/base.py` + interface `StrategicModeBuilder` | 1 j/h |
| 5 | `RegulatoryDrivenBuilder` (cas HELIOS prioritaire) | 3 j/h |
| 6 | `PerformanceDrivenBuilder` (cas MERIDIAN) | 2 j/h |
| 7 | `DataInsufficientBuilder` (cas onboarding) | 2 j/h |
| 8 | `ProcurementDrivenBuilder` + `OpportunityDrivenBuilder` (Phase 3.6 ?) | différé |
| 9 | `routes/cockpit_strategique.py` endpoint + tests intégration | 2 j/h |
| 10 | Source-guards anti-régression (test_strategique_data_driven) | 1 j/h |
| 11 | Frontend : `<StrategicModeBanner />` + `<CadreApplicable />` + `<VerdictFinal />` | 3 j/h |
| 12 | Frontend : `<ChartFrameTrajectoryLine />` + `<ChartFrameBenchSites />` | 2 j/h |
| 13 | Frontend : `pages/CockpitStrategique.jsx` + dispatcher chart | 2 j/h |
| 14 | API client `getCockpitStrategique` + route App.jsx | 0.5 j/h |
| 15 | Playwright recapture 3 modes (REGULATORY, PERFORMANCE, DATA_INSUFFICIENT) | 1 j/h |

**Total ≈ 27 j/h** Phase 3.5 stricte (3 modes prioritaires). Phase 3.6 ajoute 2 modes restants + 4 chart primitives = ~10 j/h.

---

## Open questions

1. **Verdict final** : doit-il être généré par règles métier déterministes ou par template paramétré ? Proposition : templates paramétrés v1.0, génération LLM traçable v2.0 (Phase 4+).
2. **Persona switch** : si l'utilisateur switch de DG/COMEX vers Responsable Énergie, le `strategic_mode` change-t-il ? Réponse : non, le mode est calculé du patrimoine, le persona modifie le **scoring** des highlights (cf. ADR-022) pas le mode.
3. **Multi-portefeuilles** : la page agrège-t-elle ou demande-t-elle de sélectionner ? Réponse : agrégation par défaut (filter pill `tous`), filtrage facultatif par portefeuille avec recalcul du mode.

---

**Status** : `Proposed` — à acter par Amine pour passage à `Accepted` et exécution Phase 3.5.

Auteur : session refonte Synthèse stratégique v3→v8 du 13/05/2026.
