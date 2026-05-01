# PROMPT REFONTE NARRATIVE DYNAMIQUE SYNTHÈSE STRATÉGIQUE — exécution

> **Mission** : refondre la narrative dynamique de la Synthèse stratégique selon doctrine PROMEOS Sol §11.3 + arbitrages Amine 2026-05-01 (audit `AUDIT_NARRATIVE_DYNAMIQUE.md` reçu, 5 décisions cadrage validées).
>
> **Périmètre** : 6 phases sur 4-5 semaines · ~10 source-guards pytest · 3 typologies organisationnelles MVP (grand groupe, commerce, ERP) · 6 déclencheurs hiérarchisés · push événementiel strict · mention persona · 3 maquettes HTML cibles validées.
>
> **Méthodologie** : audit-first ✓ (déjà fait — bilan `AUDIT_NARRATIVE_DYNAMIQUE.md` validé Claude externe) · phases atomiques · hard STOP gate à chaque phase · MCP Context7 + code-review + simplify obligatoires · zéro régression.
>
> **Statut** : prompt d'exécution Sprint Refonte Narrative dynamique. Successeur du sprint Cockpit Dual Sol2 validé (commit `f8d4a090`). Méthodologie identique, garde-fous identiques.

---

## 0. Hard STOP gate global — prérequis non-négociables

### 0.A — État du repo

```bash
git status
git rev-parse --abbrev-ref HEAD
```

**STOP si** : git status non clean (au-delà des fichiers harness) · branche ≠ `claude/refonte-sol2` ou successeur direct.

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

Baseline attendue post sprint Cockpit Dual : ~6 225 BE collected · 4 255 FE passed. **STOP si dégradation au-delà de cette baseline.**

### 0.D — Décisions Amine actées (cadrage 2026-05-01)

Toutes les décisions de cadrage du sprint sont actées. Récap :

| # | Décision | Phase concernée |
|---|---|---|
| 1 | Typologie scope-dynamique : org → site (Option 1.C) | Phase 1 |
| 2 | Hybride : 1 phrase événementielle + 2 phrases structurelles (Option 2.C) | Phase 3 |
| 3 | Acronymes : aucun en body, sourçage en footer (Option 3.B) | Phase 1 + Phase 4 |
| 4 | Hiérarchisation : 1 primary + 1 secondary maximum (Option 4.C) | Phase 3 |
| 5 | Panel humain : 6 personnes (2 par typologie · Option 5.B) | Phase 5 |

### 0.E — Maquettes cibles validées

3 maquettes HTML autonomes dans `docs/maquettes/narrative-sol2/` :

- `narrative-grand-groupe.html` (HELIOS, NAF holdings/sièges sociaux, vocabulaire patrimoine/CODIR)
- `narrative-commerce.html` (boulangerie, NAF 4724Z, vocabulaire métier-concret)
- `narrative-erp.html` (école/EHPAD/hôpital, NAF 8510Z/8730A/8610Z, vocabulaire usagers/élèves/résidents)

Chaque maquette contient 6 variantes de déclencheurs + 1 variante stable + mention persona + footer sourçage.

**STOP si** : Claude Code commence à coder sans avoir lu les 3 maquettes au début de la session.

### 0.F — Périmètre fichiers autorisés en écriture

**Production code** (modifications autorisées) :
- `backend/services/narrative_generator.py` — refonte cible
- `backend/services/narrative/` — nouveau sous-package (à créer)
- `backend/doctrine/naf_to_typology.py` — nouveau (à créer)
- `backend/doctrine/triggers.py` — nouveau (à créer)
- `backend/utils/naf_resolver.py` — extension
- `backend/routes/cockpit.py`, `cockpit_pages.py` — endpoint briefing
- `backend/tests/`
- `frontend/src/pages/cockpit/` — composant narrative consumer
- `frontend/src/components/cockpit/Narrative*` — nouveaux

**Documentation** :
- `docs/maquettes/narrative-sol2/`, `docs/sprints/SPRINT_NARRATIVE_DYNAMIQUE.md`

**INTERDIT pendant le sprint** :
- Toute modification `frontend/src/pages/admin/`, `backend/routes/admin*`
- Toute modification de `.github/workflows/` ou CI sans validation explicite
- Tout `git push --force` sur la branche

### 0.G — Convention de commit

Chaque phase produit **N commits atomiques** :

```
feat(narrative-sol2): Phase X.Y — description courte

- Bullet point 1 (fichier modifié + raison)
- Bullet point 2
- Source-guards ajoutés : test_xxx

Doctrine compliance: §11.3 (principe N)
Refs: AUDIT_NARRATIVE_DYNAMIQUE.md §Z
```

Aucun commit ne dépasse 500 lignes diff. Si > 500 lignes : split.

---

## 1. Phase 1 — Typologie organisationnelle (semaine 1)

### 1.A — Objectif

Créer le mapping NAF → typologie organisationnelle (3 typologies MVP) avec scope dynamique (org/site). C'est la **fondation lexicale** sur laquelle toutes les autres phases s'appuient.

### 1.B — Backlog atomique

#### Phase 1.1 — Mapping NAF → typologie

**Fichier** : `backend/doctrine/naf_to_typology.py`

```python
from enum import Enum

class OrganizationTypology(str, Enum):
    GRAND_GROUPE = "grand_groupe_tertiaire"
    COMMERCE = "commerce"
    ERP = "etablissement_recevant_public"
    # PME_TERTIAIRE et INDUSTRIE différés en V2 (Sprint Q3 2026)
    UNKNOWN = "unknown"  # fallback explicite

# Mapping NAF prefix → typologie
# Source : nomenclature NAF 2008 INSEE
NAF_PREFIX_TO_TYPOLOGY = {
    # Grand groupe tertiaire
    "64": OrganizationTypology.GRAND_GROUPE,  # holdings, finance
    "70": OrganizationTypology.GRAND_GROUPE,  # sièges sociaux
    "68": OrganizationTypology.GRAND_GROUPE,  # foncières

    # Commerce
    "47": OrganizationTypology.COMMERCE,  # commerce de détail
    "46": OrganizationTypology.COMMERCE,  # commerce de gros
    "45": OrganizationTypology.COMMERCE,  # automobile commerce
    "56": OrganizationTypology.COMMERCE,  # restauration
    "55": OrganizationTypology.COMMERCE,  # hébergement (hors hôtels publics)

    # ERP
    "85": OrganizationTypology.ERP,  # enseignement
    "86": OrganizationTypology.ERP,  # santé humaine
    "87": OrganizationTypology.ERP,  # hébergement médico-social
    "88": OrganizationTypology.ERP,  # action sociale
    "84": OrganizationTypology.ERP,  # administration publique
    "91": OrganizationTypology.ERP,  # bibliothèques, archives, musées
    "93": OrganizationTypology.ERP,  # sportif, récréatif (gymnase municipal)

    # Reste : UNKNOWN
}

def resolve_typology(naf_code: str | None) -> OrganizationTypology:
    """Résout typologie depuis NAF code."""
    if not naf_code:
        return OrganizationTypology.UNKNOWN
    prefix = naf_code[:2]
    return NAF_PREFIX_TO_TYPOLOGY.get(prefix, OrganizationTypology.UNKNOWN)
```

**Source-guards** :
- `test_naf_to_typology_grand_groupe` — NAF 6420Z (holdings) → GRAND_GROUPE
- `test_naf_to_typology_commerce` — NAF 4724Z (boulangerie) → COMMERCE
- `test_naf_to_typology_erp` — NAF 8510Z (école) → ERP
- `test_naf_to_typology_unknown_fallback` — NAF inconnu → UNKNOWN (jamais erreur)

**Commit** : `feat(narrative-sol2): Phase 1.1 — mapping NAF → typologie organisationnelle (3 MVP)`

#### Phase 1.2 — Scope dynamique : typologie selon org / site

**Fichier** : `backend/services/narrative/typology_resolver.py`

```python
def resolve_typology_for_scope(scope: dict, db: Session) -> OrganizationTypology:
    """Résout typologie selon scope :
    - Si scope = {site_id: X} → typologie du site spécifique
    - Si scope = {org_id: Y} → typologie dominante de l'org (par majorité surface)
    - Si scope = {portfolio_id: Z} → typologie dominante du portefeuille

    HELIOS (5 sites mix tertiaire) → GRAND_GROUPE (majorité bureau/hôtel/école)
    Hôtel Nice (NAF 5510Z) → ERP (si drill-down site)
    """
    if "site_id" in scope:
        site = db.query(Site).filter(Site.id == scope["site_id"]).first()
        return resolve_typology(site.naf_code if site else None)

    if "org_id" in scope:
        # Calcul typologie dominante par surface pondérée
        sites = db.query(Site).filter(Site.org_id == scope["org_id"]).all()
        if not sites:
            return OrganizationTypology.UNKNOWN
        typology_surface = {}
        for site in sites:
            typo = resolve_typology(site.naf_code)
            typology_surface[typo] = typology_surface.get(typo, 0) + (site.surface_m2 or 0)
        return max(typology_surface, key=typology_surface.get)

    return OrganizationTypology.UNKNOWN
```

**Source-guards** :
- `test_typology_helios_org_grand_groupe` — scope HELIOS org_id=1 → GRAND_GROUPE
- `test_typology_helios_hotel_nice_erp` — scope site_id=4 (Hôtel Nice NAF 5510Z) → COMMERCE
- `test_typology_resolver_no_sites_unknown` — org sans sites → UNKNOWN

**Commit** : `feat(narrative-sol2): Phase 1.2 — typology resolver scope-dynamique (org/site)`

#### Phase 1.3 — Templates lexicaux par typologie

**Fichier** : `backend/services/narrative/lexical_templates.py`

Pour chaque typologie, définir les templates lexicaux :

```python
LEXICAL_TEMPLATES = {
    OrganizationTypology.GRAND_GROUPE: {
        "scope_singular": "votre patrimoine",
        "scope_plural": "vos sites",
        "decision_body": "comité de direction",
        "decision_short": "CODIR",
        "owner_term": "Asset Manager",
        "structural_term": "portefeuille",
        "regulatory_audience": "expert",
        "avg_lecture_seconds": 180,  # 3 min CFO
    },
    OrganizationTypology.COMMERCE: {
        "scope_singular": "votre {activity}",  # boulangerie, magasin, etc.
        "scope_plural": "vos {activity}s",
        "decision_body": "vous-même en tant que propriétaire",
        "decision_short": "vous-même",
        "owner_term": "propriétaire",
        "structural_term": "activité",
        "regulatory_audience": "pédagogique",
        "avg_lecture_seconds": 60,  # 1 min commerçant
    },
    OrganizationTypology.ERP: {
        "scope_singular": "votre établissement",
        "scope_plural": "vos établissements",
        "decision_body": "conseil d'administration",
        "decision_short": "comité de direction",
        "owner_term": "directeur/directrice",
        "structural_term": "établissement",
        "regulatory_audience": "pédagogique-pro",
        "avg_lecture_seconds": 120,  # 2 min directeur
    },
    OrganizationTypology.UNKNOWN: {
        # Fallback grand groupe (audience experte par défaut)
        # ...
    },
}

def get_template(typology: OrganizationTypology, key: str, fallback: str = "") -> str:
    """Récupère template lexical avec fallback safe."""
    templates = LEXICAL_TEMPLATES.get(typology, LEXICAL_TEMPLATES[OrganizationTypology.UNKNOWN])
    return templates.get(key, fallback)
```

Il faudra aussi enrichir avec les variations de NAF dans Commerce (boulangerie / magasin / restaurant) :

```python
NAF_TO_ACTIVITY_NAME = {
    "4724Z": "boulangerie",
    "4711F": "supermarché",
    "4781Z": "stand de marché",
    "5510Z": "hôtel",  # mais ERP plutôt
    "5630Z": "restaurant",
    # ...
}

def get_activity_name(naf_code: str) -> str:
    """Retourne le nom métier concret pour la narrative."""
    return NAF_TO_ACTIVITY_NAME.get(naf_code, "magasin")
```

**Source-guards** :
- `test_lexical_template_grand_groupe_uses_patrimoine` — template GRAND_GROUPE mentionne "patrimoine"
- `test_lexical_template_commerce_uses_activity` — template COMMERCE mentionne "votre {activity}"
- `test_lexical_template_erp_uses_etablissement` — template ERP mentionne "établissement"
- `test_lexical_template_no_codir_in_commerce` — template COMMERCE ne contient JAMAIS "CODIR"
- `test_lexical_template_no_patrimoine_in_commerce` — template COMMERCE ne contient JAMAIS "patrimoine"

**Commit** : `feat(narrative-sol2): Phase 1.3 — templates lexicaux par typologie + activity name`

#### Phase 1.4 — Override utilisateur typologie

**Fichier** : extension `backend/models/user_preference.py`

```python
class UserPreference(Base):
    # ... existing fields
    typology_override: Mapped[OrganizationTypology | None] = mapped_column(
        Enum(OrganizationTypology), nullable=True,
        doc="Si défini, surcharge la typologie auto-détectée par NAF"
    )
```

**Endpoint** : `PUT /api/user/preferences/typology` pour override

**Source-guard** : `test_typology_user_override_priority` — si `user.typology_override` set, prend priorité sur NAF

**Commit** : `feat(narrative-sol2): Phase 1.4 — override utilisateur typologie + endpoint`

### 1.C — Definition of Done Phase 1

- [ ] Mapping NAF → 3 typologies MVP livré + UNKNOWN fallback
- [ ] Resolver scope-dynamique (org/site) livré
- [ ] Templates lexicaux 3 typologies livrés
- [ ] Activity name mapping pour commerce livré
- [ ] Override utilisateur livré + endpoint
- [ ] 8 source-guards créés et verts
- [ ] Tests baseline maintenus
- [ ] 4 commits atomiques

---

## 2. Phase 2 — Push événementiel "+X vs S-1" (semaine 1-2)

### 2.A — Objectif

Tisser les `weekly_deltas` (déjà exposés Phase 3.3 sprint Cockpit Dual mais non consommés par narrative) dans le body de la narrative selon Option 3.C (push strict, silence accepté quand stable).

### 2.B — Backlog atomique

#### Phase 2.1 — Helper push événementiel

**Fichier** : `backend/services/narrative/event_push.py`

```python
def should_push_metric(metric_name: str, current: float, previous: float) -> bool:
    """Décide si on push un signal selon Option 3.C (push strict).

    Règles silence éditorial :
    - Variation < 5 % en relatif → silence
    - Variation < 1 k€ en absolu (pour exposure) → silence
    - Variation < 5 MWh/an (pour potential) → silence
    """
    if previous == 0 or previous is None:
        return False
    relative_pct = abs((current - previous) / previous) * 100

    thresholds = {
        "exposure_eur": (5.0, 1000),  # 5% OR 1 k€
        "potential_mwh_year": (5.0, 5),  # 5% OR 5 MWh
        "compliance_score": (3.0, None),  # 3 points
        "sites_in_drift": (None, 1),  # 1 site
    }

    rel_threshold, abs_threshold = thresholds.get(metric_name, (5.0, None))

    if rel_threshold and relative_pct < rel_threshold:
        if abs_threshold is None or abs(current - previous) < abs_threshold:
            return False
    return True

def format_push_clause(metric_name: str, current: float, previous: float, typology: OrganizationTypology) -> str:
    """Formate la clause "+X vs S-1" en respectant le ton typologique.

    Grand groupe : "+ 18 % vs semaine précédente"
    Commerce : "+ 14 % vs la semaine dernière"
    ERP : "+ 14 % vs semaine dernière"
    """
    delta = current - previous
    relative_pct = (delta / previous) * 100 if previous else 0
    direction = "+ " if delta > 0 else "− "

    if typology == OrganizationTypology.COMMERCE:
        return f"{direction}{abs(relative_pct):.0f} % vs la semaine dernière"
    return f"{direction}{abs(relative_pct):.0f} % vs semaine précédente"
```

**Source-guards** :
- `test_push_silence_below_5pct` — variation 3 % → push silence
- `test_push_active_above_5pct` — variation 18 % → push actif
- `test_push_silence_below_1keur` — variation 800 € → push silence
- `test_push_format_grand_groupe_vs_commerce` — formats lexicaux corrects par typologie

**Commit** : `feat(narrative-sol2): Phase 2.1 — push event helper (Option 3.C silence éditorial strict)`

#### Phase 2.2 — Injection dans narrative_generator

Modification de `narrative_generator.build_cockpit_comex_briefing` :

```python
def build_cockpit_comex_briefing(facts: dict, persona: Persona, typology: OrganizationTypology) -> dict:
    weekly_deltas = facts.get("weekly_deltas", {})

    # Détecter quels deltas méritent un push
    pushes = []
    for metric_name, delta_data in weekly_deltas.items():
        if should_push_metric(metric_name, delta_data["current"], delta_data["previous"]):
            pushes.append({
                "metric": metric_name,
                "clause": format_push_clause(metric_name, delta_data["current"], delta_data["previous"], typology),
                "magnitude": abs(delta_data["current"] - delta_data["previous"]),
            })

    # Tri par magnitude décroissante, max 1 push (Option 4.C)
    pushes.sort(key=lambda p: p["magnitude"], reverse=True)
    primary_push = pushes[0] if pushes else None

    # Tisser dans body
    body = compose_body(facts, persona, typology, primary_push)
    return {"narrative_text": body, "pushes_detected": len(pushes), ...}
```

**Source-guards** :
- `test_narrative_includes_weekly_push_when_active` — si push actif, narrative contient "vs semaine"
- `test_narrative_silence_when_no_push` — si tout sous seuil, narrative ne contient PAS "vs semaine"
- `test_narrative_max_one_push` — max 1 push même si plusieurs metrics dépassent seuil

**Commit** : `feat(narrative-sol2): Phase 2.2 — injection push événementiel dans body narrative`

### 2.C — Definition of Done Phase 2

- [ ] Helper push event livré avec règles silence éditorial
- [ ] Format push clause par typologie livré
- [ ] Injection dans narrative_generator livrée
- [ ] 7 source-guards créés et verts
- [ ] Tests baseline maintenus
- [ ] 2 commits atomiques

---

## 3. Phase 3 — Hiérarchisation déclencheurs primary/secondary (semaines 2-3)

### 3.A — Objectif

Mapper les 9 detectors `event_bus` sur les 6 déclencheurs cibles doctrinaux + hiérarchiser primary/secondary (Option 4.C — max 1 primary + 1 secondary tissés en body).

### 3.B — Backlog atomique

#### Phase 3.1 — 6 déclencheurs cibles définis

**Fichier** : `backend/doctrine/triggers.py`

```python
class TriggerType(str, Enum):
    DT_TRAJECTORY_DRIFT = "dt_trajectory_drift"  # priorité 1
    MAJOR_ANOMALY = "major_anomaly"  # priorité 2
    EXPOSURE_VARIATION = "exposure_variation"  # priorité 3
    AUDIT_DEADLINE_IMMINENT = "audit_deadline_imminent"  # priorité 4
    PURCHASE_WINDOW_OPEN = "purchase_window_open"  # priorité 5
    COMPLIANCE_THRESHOLD_CROSSED = "compliance_threshold_crossed"  # priorité 6

TRIGGER_PRIORITY = {
    TriggerType.DT_TRAJECTORY_DRIFT: 1,
    TriggerType.MAJOR_ANOMALY: 2,
    TriggerType.EXPOSURE_VARIATION: 3,
    TriggerType.AUDIT_DEADLINE_IMMINENT: 4,
    TriggerType.PURCHASE_WINDOW_OPEN: 5,
    TriggerType.COMPLIANCE_THRESHOLD_CROSSED: 6,
}

# Mapping : 9 detectors event_bus → 6 cibles narrative
DETECTOR_TO_TRIGGER = {
    "consumption_drift": TriggerType.DT_TRAJECTORY_DRIFT,
    "trajectory_off_track": TriggerType.DT_TRAJECTORY_DRIFT,
    "billing_anomaly": TriggerType.MAJOR_ANOMALY,
    "data_quality_issue": None,  # masqué — non saillant pour narrative
    "asset_registry_issue": None,  # masqué
    "action_overdue": TriggerType.MAJOR_ANOMALY,
    "compliance_deadline": TriggerType.AUDIT_DEADLINE_IMMINENT,
    "contract_renewal": TriggerType.PURCHASE_WINDOW_OPEN,
    "market_window": TriggerType.PURCHASE_WINDOW_OPEN,
    "flex_opportunity": None,  # masqué — pas un déclencheur narrative principal
}

# Triggers MASQUÉS par typologie
MASKED_TRIGGERS_BY_TYPOLOGY = {
    OrganizationTypology.COMMERCE: {
        TriggerType.COMPLIANCE_THRESHOLD_CROSSED,  # score abstrait pour commerçant
        TriggerType.EXPOSURE_VARIATION,  # remplacé par variation coût direct
    },
    OrganizationTypology.ERP: set(),  # tous actifs
    OrganizationTypology.GRAND_GROUPE: set(),  # tous actifs
}
```

**Source-guards** :
- `test_trigger_priorities_consistent` — 6 triggers ont priorités 1-6 distinctes
- `test_detector_mapping_complete` — 9 detectors mappés (ou explicitement None)
- `test_masked_triggers_commerce` — COMPLIANCE_THRESHOLD_CROSSED masqué pour COMMERCE

**Commit** : `feat(narrative-sol2): Phase 3.1 — 6 déclencheurs hiérarchisés + mapping detectors`

#### Phase 3.2 — Trigger prioritizer

**Fichier** : `backend/services/narrative/trigger_prioritizer.py`

```python
def prioritize_triggers(events: list[SolEventCard], typology: OrganizationTypology) -> dict:
    """Hiérarchise les events détectés en primary + secondary selon Option 4.C.

    Returns:
        {
            "primary": TriggerType | None,
            "primary_event": SolEventCard | None,
            "secondary": TriggerType | None,
            "secondary_event": SolEventCard | None,
            "all_active_triggers": list[TriggerType],
        }
    """
    # 1. Mapper events → triggers (filtrer None)
    triggered = []
    for event in events:
        trigger = DETECTOR_TO_TRIGGER.get(event.detector_name)
        if trigger and trigger not in MASKED_TRIGGERS_BY_TYPOLOGY.get(typology, set()):
            triggered.append((trigger, event))

    # 2. Trier par priorité ascendante (1 = plus urgent)
    triggered.sort(key=lambda x: TRIGGER_PRIORITY[x[0]])

    # 3. Dédupliquer (même trigger = on ne garde que le plus saillant)
    seen = set()
    unique = []
    for trigger, event in triggered:
        if trigger not in seen:
            seen.add(trigger)
            unique.append((trigger, event))

    # 4. Extraire primary + secondary
    primary = unique[0] if unique else (None, None)
    secondary = unique[1] if len(unique) >= 2 else (None, None)

    return {
        "primary": primary[0],
        "primary_event": primary[1],
        "secondary": secondary[0],
        "secondary_event": secondary[1],
        "all_active_triggers": [t for t, _ in unique],
    }
```

**Source-guards** :
- `test_prioritizer_returns_top_priority` — multiple triggers → primary = priorité 1
- `test_prioritizer_max_2_in_body` — primary + secondary, jamais 3+ tissés
- `test_prioritizer_masks_compliance_for_commerce` — score conformité jamais primary pour commerce
- `test_prioritizer_silence_when_no_trigger` — aucun event → primary = None (pas d'erreur)

**Commit** : `feat(narrative-sol2): Phase 3.2 — trigger prioritizer (Option 4.C primary + secondary max)`

#### Phase 3.3 — Composition phrase 1 événementielle

**Fichier** : `backend/services/narrative/sentence_composer.py`

```python
def compose_sentence_1_eventful(prioritization: dict, typology: OrganizationTypology) -> str:
    """Phrase 1 événementielle : raconte le primary trigger.
    Si pas de primary → phrase de stabilité."""
    primary = prioritization["primary"]
    primary_event = prioritization["primary_event"]

    if not primary:
        # Variante stable
        return SENTENCE_STABLE_BY_TYPOLOGY[typology]

    # Trigger-specific composer
    composer = TRIGGER_TO_COMPOSER.get(primary)
    return composer(primary_event, typology)

def compose_dt_drift_sentence(event, typology: OrganizationTypology) -> str:
    sites_count = event.metadata.get("sites_in_drift", 1)
    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"{sites_count} sites de votre patrimoine ont basculé en dérive de la trajectoire 2030 cette semaine"
    if typology == OrganizationTypology.COMMERCE:
        activity = event.metadata.get("activity_name", "magasin")
        return f"Votre {activity} consomme 18 % de plus que les {activity}s similaires de votre région cette semaine"
    if typology == OrganizationTypology.ERP:
        return f"Votre établissement a basculé en dérive de la trajectoire 2030 cette semaine"
    return ""
```

**Source-guards** :
- `test_sentence_1_drift_grand_groupe_has_patrimoine` — phrase grand groupe contient "patrimoine"
- `test_sentence_1_drift_commerce_no_patrimoine` — phrase commerce ne contient PAS "patrimoine"
- `test_sentence_1_stable_when_no_trigger` — pas de trigger → phrase de stabilité spécifique

**Commit** : `feat(narrative-sol2): Phase 3.3 — composition phrase 1 événementielle par typologie`

### 3.C — Definition of Done Phase 3

- [ ] 6 déclencheurs cibles définis avec priorités
- [ ] Mapping 9 detectors → 6 triggers livré
- [ ] Triggers masqués par typologie (commerce) livrés
- [ ] Trigger prioritizer livré (max primary + secondary)
- [ ] Composition phrase 1 événementielle par typologie livrée
- [ ] 10 source-guards créés et verts
- [ ] Tests baseline maintenus
- [ ] 3 commits atomiques

---

## 4. Phase 4 — Mention persona + variation tonale (semaine 3)

### 4.A — Objectif

Injecter mention persona-spécifique en italique (Option 1.C) + exploiter `narrative_tone` calculé pour faire varier le lexique (alarme/stable/amélioration).

### 4.B — Backlog atomique

#### Phase 4.1 — Persona context

**Fichier** : `backend/services/narrative/persona_context.py`

```python
class PersonaRole(str, Enum):
    DG = "dg"
    CFO = "cfo"
    ASSET_MANAGER = "asset_manager"
    PROPERTY_MANAGER = "property_manager"
    ENERGY_MANAGER = "energy_manager"
    DIRECTOR_ERP = "director_erp"
    OWNER_COMMERCE = "owner_commerce"

PERSONA_FOCUS = {
    PersonaRole.CFO: "P&L",
    PersonaRole.DG: "stratégie",
    PersonaRole.ASSET_MANAGER: "performance asset",
    PersonaRole.OWNER_COMMERCE: "économies directes",
    PersonaRole.DIRECTOR_ERP: "service public + budget",
    # ...
}

def compose_persona_mention(user_first_name: str, user_role: PersonaRole, facts: dict, typology: OrganizationTypology) -> str:
    """Compose la mention persona italique.

    Format : "Pour {Prénom}, {rôle court} : {focus chiffre adapté}"
    """
    focus_text = compute_persona_focus_text(user_role, facts, typology)
    role_short = PERSONA_ROLE_LABEL.get(user_role, "responsable")
    return f"Pour {user_first_name}, {role_short} : {focus_text}"
```

**Source-guards** :
- `test_persona_mention_cfo_mentions_pnl` — mention CFO contient "P&L" ou "budget"
- `test_persona_mention_owner_commerce_simple` — mention propriétaire commerce simple, pas de jargon
- `test_persona_mention_director_erp_service` — mention directeur ERP mentionne service ou conseil

**Commit** : `feat(narrative-sol2): Phase 4.1 — mention persona italique (Option 1.C)`

#### Phase 4.2 — Variation tonale

**Fichier** : `backend/services/narrative/tone_variator.py`

```python
class NarrativeTone(str, Enum):
    ALARM = "alarm"  # exposition montante, dérive critique
    WATCH = "watch"  # signaux faibles, vigilance
    STABLE = "stable"  # patrimoine stable
    IMPROVEMENT = "improvement"  # amélioration vs S-1

# Lexique par tonalité (déjà calculé en `narrative_tone`)
TONE_LEXICON = {
    NarrativeTone.ALARM: {
        "verb_state": "expose",  # "expose 26 k€"
        "intro_qualifier": "significativement",
    },
    NarrativeTone.STABLE: {
        "verb_state": "présente",  # "présente une exposition"
        "intro_qualifier": "stable",
    },
    NarrativeTone.IMPROVEMENT: {
        "verb_state": "réduit",
        "intro_qualifier": "favorablement",
    },
    NarrativeTone.WATCH: {
        "verb_state": "présente",
        "intro_qualifier": "à surveiller",
    },
}

def apply_tone(sentence_template: str, tone: NarrativeTone) -> str:
    """Substitue les placeholders {verb_state}, {intro_qualifier} selon ton."""
    lexicon = TONE_LEXICON[tone]
    return sentence_template.format(**lexicon)
```

**Source-guards** :
- `test_tone_alarm_uses_expose` — narrative en mode alarme contient "expose"
- `test_tone_stable_uses_presente` — narrative en mode stable contient "présente"
- `test_tone_no_alarm_when_score_above_70` — score > 70/100 → pas de tone alarm

**Commit** : `feat(narrative-sol2): Phase 4.2 — variation tonale alarme/stable/amélioration`

### 4.C — Definition of Done Phase 4

- [ ] Persona context + 3 personas mappés livrés
- [ ] Variation tonale livrée
- [ ] 6 source-guards créés et verts
- [ ] 2 commits atomiques

---

## 5. Phase 5 — Validation utilisateur réelle (semaines 4-5)

### 5.A — Objectif

Test doctrinal §11.3 DoD avec **6 humains réels** (Option 5.B). Pas de proxy IA cette fois — c'est intégré dès la planification.

### 5.B — Protocole de test

#### Phase 5.1 — Recrutement panel (6 personnes)

| Typologie | Profils ciblés | Compensation |
|---|---|---|
| Grand groupe tertiaire | 1 CFO ETI tertiaire (50-500 sites) + 1 Asset Manager foncière | 100 €/personne |
| Commerce | 1 boulanger propriétaire + 1 gérant 3 pharmacies | 100 €/personne |
| ERP | 1 directeur école primaire + 1 directeur EHPAD | 100 €/personne |

**Total budget** : 600 €.

**Délai recrutement** : 2-3 semaines en parallèle des phases dev.

**Critères de réussite (par typologie)** :

- 100 % des panels identifient en 3 min au moins 4 critères principaux sur 5 (selon grille Phase 4.B Cockpit Dual)
- 100 % des panels confirment que la narrative leur "parle" (vocabulaire métier juste)
- 0 panel n'utilise des mots comme "incompréhensible", "abstrait", "trop technique"

#### Phase 5.2 — Sessions test 3 min chronométrées

Protocole strict identique au Sprint Cockpit Dual Phase 4 :

1. Présentation neutre : « Je vais vous montrer une page web pendant 3 minutes »
2. Affichage de la Synthèse stratégique scope adapté à la typologie testée
3. Chronomètre 3 min, aucune intervention
4. Question : « En 30 secondes, dites-moi ce que vous avez compris et ce que vous feriez »
5. Enregistrement audio (avec consentement) + verbatim mot pour mot

#### Phase 5.3 — Itération sur retours

Pour chaque critère non atteint :
- Documenter dans `docs/sprints/SPRINT_NARRATIVE_DYNAMIQUE.md`
- Mini-sprint correctif (1-2 j) avant validation finale
- Re-test sur 1-2 panels rappelés

### 5.C — Definition of Done Phase 5

- [ ] 6 personnes recrutées + signatures consentement
- [ ] 6 sessions test enregistrées + verbatim documenté
- [ ] Compte-rendu structuré dans `outputs/phase_5_user_tests.md`
- [ ] Critères validés/invalidés documentés par typologie
- [ ] Mini-sprints correctifs effectués si nécessaire

---

## 6. Phase 6 — `simulate_date` paramètre fonctionnel (semaine 5)

### 6.A — Objectif

Implémenter le paramètre `simulate_date` actuellement accepté HTTP 200 mais ignoré (révélé par audit). Permet de tester la dynamique narrative J vs J+30 sans attendre le temps réel.

### 6.B — Backlog atomique

#### Phase 6.1 — Implémentation simulate_date

**Modification** : `narrative_generator.build_briefing(facts, persona, typology, simulate_date=None)`

Si `simulate_date` fourni :
- Override `now()` interne par cette date
- Calcul deltas vs S-1 = simulate_date - 7 jours
- Tous les déclencheurs évalués comme si on était à `simulate_date`

**Source-guard** : `test_simulate_date_changes_narrative` — narrative à J vs J+30 doit différer si données ont évolué

**Commit** : `feat(narrative-sol2): Phase 6.1 — simulate_date paramètre fonctionnel`

### 6.C — Definition of Done Phase 6

- [ ] `simulate_date` fonctionnel
- [ ] Source-guard passe
- [ ] 1 commit atomique

---

## 7. Definition of Done Sprint global

- [ ] Phases 1 à 6 complétées
- [ ] ~30 source-guards pytest verts en CI
- [ ] Tests baseline 6 225 BE + 4 255 FE maintenus tout au long
- [ ] 6 humains testés dans Phase 5 avec critères validés
- [ ] 3 maquettes cibles `narrative-grand-groupe`, `narrative-commerce`, `narrative-erp` matérialisées en production
- [ ] Doctrine §11.3 compliance documentée dans PR finale
- [ ] Commit final tag `narrative-dynamique-v1.0`

---

## 8. Ce qui n'est PAS dans ce sprint (à acter explicitement)

- **Typologies PME tertiaire et Industrie** : différées en V2 (Sprint Q3 2026)
- **Personnalisation narrative au niveau de la phrase 2-3** : ce sprint personnalise phrase 1 + mention persona, les phrases structurelles restent communes
- **Internationalisation** : tout reste en français
- **Test utilisateur > 6 personnes** : Phase 5 vise 6, études quantitatives plus larges = sprint UX research séparé
- **Refonte autres pages narratives** (Patrimoine, Conformité, Bill Intel) : ce sprint refond uniquement Cockpit Synthèse stratégique
- **Voix audio narrative** (text-to-speech) : hors scope

---

## 9. Risques identifiés et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Recrutement panel humain Phase 5 | Élevée | Élevé | Démarrer recrutement dès Phase 1 (semaine 1) en parallèle |
| Doctrine ambiguë sur typologie HELIOS (mix tertiaire) | Moyenne | Moyen | Décision : Option 1.C scope-dynamique tranchée. HELIOS scope org → GRAND_GROUPE |
| Templates lexicaux trop nombreux à écrire | Moyenne | Moyen | Limiter à 6 templates par typologie (1 par déclencheur) + 1 stable. Total : 21 templates |
| Acronymes en body → lecture cassée | Faible | Élevé | Source-guard explicite `test_no_acronym_in_body` |
| Push événementiel quand instable artificiellement | Moyenne | Moyen | Seuils silence éditorial (5 % OR 1 k€) tranchés en Phase 2.1 |

---

## 10. Convention de fin de sprint

À la fin du sprint :

1. PR finale avec le tag `narrative-dynamique-v1.0`
2. Compte-rendu détaillé par phase dans `docs/sprints/SPRINT_NARRATIVE_DYNAMIQUE.md`
3. Captures Playwright avant/après narrative dans `docs/captures/narrative-before-after/`
4. Compte-rendu Phase 5 panel humain (verbatims + analyses)
5. Sprint retro Amine ↔ Claude Code

---

**Sprint Refonte Narrative dynamique Synthèse stratégique — exécution — méthodologie PROMEOS doctrine v1.0 §11.3 + arbitrages Amine 2026-05-01**
