---
name: cee-p6
description: Use whenever working on French Certificats d'Économies d'Énergie programme P6 (2026-2030) in HELIOS — fiches BAT-* (BAT-EN, BAT-TH, BAT-EQ, BAT-SE), calcul kWhc cumac, zones climatiques H1a-H3, catalogue cee_p6_catalog.yaml, opportunités financement éco-travaux. Triggers on edits in backend/regops/rules/cee_p6.py, backend/regops/config/cee_p6_catalog.yaml, backend/services/cee_service.py, or any task mentioning CEE, P5/P6, fiches BAT-EN/BAT-TH/BAT-EQ/BAT-SE, kWhc cumac, MWhc, zones climatiques, durée de vie conventionnelle, opportunités CEE, financement BACS/APER/DT par CEE.
---

# CEE P6 — Discipline Certificats d'Économies d'Énergie période 6 (2026-2030)

Skill métier régulatoire. Hérite de `audit-then-fix` (méthodo socle). Cette Skill ajoute les règles spécifiques au programme CEE période 6 : routage catalogue, nomenclature fiches, formule kWhc cumac, distinction opportunité vs obligation.

## Relation avec `promeos-regulatory`

Deux Skills couvrent le CEE P6 PROMEOS, avec des rôles distincts et complémentaires :

| Skill | Rôle | Triggers |
|---|---|---|
| `promeos-regulatory` | **Expertise métier** : programme CEE, période P6 2026-2030, obligés/délégataires, catalogue officiel fiches DGEC, jurisprudence, transition P5→P6 | Questions "qu'est-ce qu'une fiche BAT-TH-…", "comment se calcule un kWhc cumac…", "quelle fiche pour…", veille arrêtés CEE |
| `cee-p6` (cette Skill) | **Discipline d'édition** : règles non-négociables quand on modifie le code CEE (routage catalogue YAML, nomenclature fiches, formule canonique, exhaustivité, tests) | Édition `backend/regops/rules/cee_p6.py`, `backend/regops/config/cee_p6_catalog.yaml`, `backend/services/cee_service.py`, ajout fiche BAT-*, refacto moteur kWhc cumac |

**Règles de précédence** :

- Question conceptuelle CEE pure → `promeos-regulatory` répond, `cee-p6` ne s'active pas.
- Édition de code CEE → `cee-p6` est **prioritaire et bloquant** sur le diff. `promeos-regulatory` peut être consulté pour valider le fond métier (ex : nouvelle fiche DGEC à ajouter).
- Conflit apparent entre les deux → `cee-p6` gagne sur la forme (où mettre la valeur, comment la nommer, comment la tester). `promeos-regulatory` gagne sur le fond (quelle fiche, quels coefficients, quelle durée de vie).

**Pour les audits régulatoires complexes** (ajout massif de fiches, refacto moteur calcul, mise à jour P5→P6), déléguer à l'agent `regulatory-expert` via Task tool (cf. CLAUDE.md). Cette Skill cadre les règles d'édition ; `regulatory-expert` exécute les tâches lourdes avec validation métier.

## Sources de vérité

| SoT | Rôle |
|---|---|
| `backend/regops/config/cee_p6_catalog.yaml` | **Catalogue canonique** des fiches CEE P6 (BAT-EN-*, BAT-TH-*, BAT-EQ-*, BAT-SE-*) + coefficients zones climatiques H1a-H3 + correspondance département→zone. Toute fiche se définit ici, nulle part ailleurs. |
| `backend/regops/rules/cee_p6.py` | Moteur calcul `compute_cee_kwh_cumac()` + helpers `get_fiche()`, `get_zone_coefficient()`, `resolve_zone_from_code_postal()`. Loader avec cache singleton `_catalog_cache`. |
| `backend/doctrine/constants.py` | Constantes inviolables CEE (prix MWhc cumac, zone fallback). **TODO connu** : `CEE_PRIX_MWHC_CUMAC_EUR` cité dans `CeeCalculResult.amount_eur` mais n'existe pas encore en constante doctrine — à canoniser (cf. Discipline 1). |
| `backend/services/cee_service.py` | Service exposé API consommant le moteur. Pas de duplication de logique catalogue. |

Toute donnée CEE en runtime doit transiter par l'un de ces points. Aucune autre voie.

## Discipline 1 — Routage catalogue + constantes prix

**Règle catalogue** : tout calcul, scoring, ou affichage qui dépend d'une fiche CEE (typical_savings_kwh_m2, duree_vie_ans, label, category) doit passer par `get_fiche(fiche_ref)` → `cee_p6_catalog.yaml`. Jamais de fiche hardcodée inline.

### État actuel (à corriger)

`CeeCalculResult.amount_eur` (docstring `backend/regops/rules/cee_p6.py`) cite `CEE_PRIX_MWHC_CUMAC_EUR`, mais cette constante **n'existe pas** encore dans `backend/doctrine/constants.py`. Audit vérifié en Phase 0 lors de la relecture Skill cee-p6 (02/05/2026).

**Tracking** : EPIC issue "Alignement Skills × architecture HELIOS post-série", task "Canonisation CEE constantes".

### Action de canonisation requise

Créer dans `backend/doctrine/constants.py` :

```python
CEE_PRIX_MWHC_CUMAC_EUR = 8.50  # prix moyen marché CEE P6 2026 (DGEC + observatoire EMMY)
CEE_ZONE_CLIMATIQUE_FALLBACK = "H2b"  # convention métier PROMEOS (cf. Discipline 4)
```

### Pattern AVANT canonisation (transitoire)

```python
# Tant que CEE_PRIX_MWHC_CUMAC_EUR n'existe pas dans constants.py, le moteur
# applique son défaut 8.50 défini dans la signature compute_cee_kwh_cumac().
# Toute modification du prix doit déclencher la canonisation simultanément.
result = compute_cee_kwh_cumac(
    fiche_ref="BAT-EN-101",
    surface_m2=site.surface_m2,
    code_postal=site.code_postal,
    # prix_mwhc_cumac_eur omis → défaut 8.50 (TODO canoniser, voir EPIC issue)
)
```

### Pattern APRÈS canonisation (cible)

```python
# 1. Catalogue canonique — UNIQUEMENT cee_p6_catalog.yaml
"BAT-EN-101": {label: "Isolation combles/toiture", typical_savings_kwh_m2: 50, duree_vie_ans: 30}

# 2. Constante prix canonique — backend/doctrine/constants.py
CEE_PRIX_MWHC_CUMAC_EUR = 8.50

# 3. Usage côté services / rules
from backend.regops.rules.cee_p6 import compute_cee_kwh_cumac
from backend.doctrine.constants import CEE_PRIX_MWHC_CUMAC_EUR
result = compute_cee_kwh_cumac(
    fiche_ref="BAT-EN-101",
    surface_m2=site.surface_m2,
    code_postal=site.code_postal,
    prix_mwhc_cumac_eur=CEE_PRIX_MWHC_CUMAC_EUR,
)
```

### Anti-patterns (toujours valables, AVANT et APRÈS canonisation)

- `kwh_cumac = 50 * surface * 1.3 * 30` en dur dans une route ou service → refusé (passer par `compute_cee_kwh_cumac("BAT-EN-101", surface, code_postal=...)`)
- Réplication des coefficients zones (H1a=1.3, etc.) dans un autre fichier que le YAML → refusé
- Hardcoder un prix `prix_mwhc=9.00` ailleurs que dans `constants.py` après canonisation → refusé
- Hardcoder une fiche dans un test sans passer par `get_fiche()` → refusé (les tests valident le routage, pas la duplication)

## Discipline 2 — Nomenclature CEE canonique

**Vocabulaire canonique** :

| Terme | Statut | Usage autorisé |
|---|---|---|
| `CEE_P6` | ✅ Code régulation canonique | `Finding.regulation`, scoring, API |
| `BAT-EN-NNN` / `BAT-TH-NNN` / `BAT-EQ-NNN` / `BAT-SE-NN` | ✅ Codes fiches canoniques | Clés YAML, `fiche_ref`, labels UI |
| `kWhc cumac` | ✅ Unité canonique | Variables, labels UI principal, docs |
| `MWhc cumac` | ✅ Unité dérivée | Conversion EUR (× prix / 1000) |
| `zone climatique H1a-H3` | ✅ 8 zones canoniques | YAML, `zone_climatique` champ |
| `CEE` (sans P6) | ⚠️ Acceptable label UI court | Tooltips, mentions générales |

**Règles strictes** :

- Code interne `regulation` → `"CEE_P6"` (snake majuscules) uniquement. Jamais `"cee_p6"`, `"CEE"` seul, ou `"P6"` seul.
- Codes fiches → format `BAT-XX-NNN` strict. Jamais `bat-en-101` ou `BATEN101` ou `BAT_EN_101`.
- Variables Python : `kwh_cumac` (jamais `kwhc`, `kwh_cumac_kwh`, `cumac_kwh`).
- Zones climatiques : `H1a, H1b, H1c, H2a, H2b, H2c, H2d, H3` strict. Jamais `H1`, `H2`, `Zone-1`, etc.
- Labels UI : "Fiche BAT-EN-101 (Isolation combles/toiture)" acceptable, "Fiche 101" sans préfixe BAT-EN refusé.

**Catégories canoniques** (clé `category` YAML, **7 valeurs strictes**) :

| Code | Description |
|---|---|
| `envelope` | Isolation, étanchéité (combles, murs, planchers, toiture) |
| `heating` | Chauffage, ECS, chaudière, pompes à chaleur |
| `ventilation` | VMC, double-flux, récupération chaleur |
| `lighting` | LED, gestion éclairage |
| `controls` | GTB, GTC, supervision, BACS |
| `renewables` | Solaire thermique/PV, géothermie, biomasse |
| `services` | CPE, audit, accompagnement (calcul `typical_savings_pct`, pas `kwh_m2`) |

**Anti-patterns interdits** :

- `regulation="CEE"` → refusé (utiliser `"CEE_P6"`)
- Variable `kwhc_cumac` → refusé (renommer `kwh_cumac`)
- Catégorie `"isolation"` au lieu de `"envelope"` → refusé
- Zone `"H1"` au lieu de `"H1a"` → refusé (perte de précision)

## Discipline 3 — Régulation opportunité, pas obligation

**Règle critique** : CEE P6 est une **régulation opportunité** (financement éco-travaux), pas une obligation de conformité. Conséquences sur tout `Finding` produit par `cee_p6.py` :

- `Finding.status` = **`"COMPLIANT"`** toujours (ou `"INFO"` si applicable au schéma — jamais `"NON_COMPLIANT"`, `"AT_RISK"`).
- `Finding.severity` = `"LOW"` ou `"INFO"` (jamais `"CRITICAL"`, `"HIGH"`).
- `Finding.category` = `"incentive"` (jamais `"compliance"`, `"obligation"`).
- `Finding.legal_deadline` = `None` (CEE P6 n'a pas de deadline imposée par site, juste une fenêtre programme 2026-2030).
- **Pas de pénalité** dans la Skill ou en constante. CEE P6 n'apparaît pas dans `REGOPS_WEIGHTS_*` (Discipline 5 de `decret-tertiaire`).

**Anti-patterns interdits** :

- `Finding(regulation="CEE_P6", status="NON_COMPLIANT", severity="CRITICAL")` → refusé (contresens : ne pas activer une fiche CEE n'est jamais une non-conformité)
- Ajouter `CEE_P6` à `REGOPS_WEIGHTS_AUDIT_APPLICABLE` ou `REGOPS_WEIGHTS_DEFAULT` → refusé (CEE P6 n'est pas une dimension de scoring conformité tertiaire)
- Wording UI "Vous êtes hors conformité CEE P6" → refusé (utiliser "Opportunité de financement CEE non activée : économies estimées XX kWh/m²/an")
- Créer une `CEE_P6_PENALTY_EUR` dans `constants.py` → refusé (n'existe pas réglementairement)

**Wording correct** UI / `explanation` :

- ✅ "Opportunité CEE BAT-TH-158 (système GTB) : économies estimées 35 kWh/m²/an, financement potentiel ~XX €."
- ✅ "Fiche CEE applicable, action non encore engagée."
- ❌ "Site non conforme CEE P6."

**Escape hatch — évolution réglementaire future** : si un cas réglementaire futur change ce statut (ex : CEE P6 devient quasi-obligatoire via décret modificateur, ou intégration au scoring conformité par arrêté DGEC), escalader à l'utilisateur + agent `regulatory-expert` + relire intégralement cette Skill — ne pas modifier unilatéralement le verrou opportunité.

## Discipline 4 — Formule kWhc cumac canonique

**Règle** : la formule de calcul `kWhc cumac` est **figée** par le code `compute_cee_kwh_cumac()` :

```
kWhc cumac = typical_savings_kwh_m2 × surface_m2 × zone_coefficient × duree_vie_ans
amount_eur = kwh_cumac × CEE_PRIX_MWHC_CUMAC_EUR / 1000
```

**Conséquences** :

- Pas de simplification (retirer `zone_coefficient`, retirer `duree_vie_ans`) → refusé même temporairement (drift métier garanti).
- Pas d'ajout d'un facteur multiplicateur ad-hoc (`bonus_qpv`, `coefficient_majoration`) sans validation `regulatory-expert` + arrêté DGEC officiel.
- Modifier la fonction `compute_cee_kwh_cumac()` ou ses helpers → tests de non-régression numérique obligatoires sur sites démo HELIOS (tolérance ±0.01 kWhc).
- Le fallback zone climatique = `"H2b"` est un **choix produit PROMEOS** aligné convention CEE simplifiée tertiaire (coefficient 1.0 = neutre, n'amplifie ni n'atténue). Pas issu d'un arrêté DGEC précis et citable — à ré-évaluer si le parc client réel diverge. Doit rester aligné avec `CEE_ZONE_CLIMATIQUE_FALLBACK` après canonisation (Discipline 1).

**Anti-patterns interdits** :

- `kwh_cumac = typical_savings * surface_m2 * duree_vie_ans` (oubli zone_coefficient) → refusé
- `amount_eur = kwh_cumac * 8.50` (oubli division par 1000, confusion kWhc vs MWhc) → refusé
- Modifier le moteur sans test de non-régression sur fixtures `BAT-EN-101 + H2b + 1000m²` → refusé

## Discipline 5 — Exhaustivité catalogue YAML

**Règle** : ajouter une fiche CEE = ajout YAML uniquement, jamais de hardcoded Python.

**Champs obligatoires** par fiche dans `cee_p6_catalog.yaml` :

| Champ | Type | Requis | Note |
|---|---|---|---|
| `label` | str | ✅ | Description FR user-facing |
| `category` | enum | ✅ | Une des 7 catégories canoniques (Discipline 2) |
| `typical_savings_kwh_m2` | float | ⚠️ Requis sauf services | Économies unitaires par m² |
| `typical_savings_pct` | float | ⚠️ Alternatif services | Pour `category: services` (ex CPE) |
| `duree_vie_ans` | int | ✅ | Durée de vie conventionnelle (4 à 30 ans) |

**Règles strictes** :

- Une fiche `category="services"` peut avoir `typical_savings_pct` au lieu de `typical_savings_kwh_m2` (ex : BAT-SE-06 CPE 15%). Le moteur lève `ValueError` si la fiche n'a ni l'un ni l'autre.
- Modification d'une fiche existante (typical_savings, duree_vie) → revue PR avec source officielle DGEC (arrêté CEE applicable au programme P6).
- Nouvelle fiche → cohérence avec catalogue DGEC officiel + test ajouté validant `get_fiche()` + `compute_cee_kwh_cumac()` sur la fiche.
- Coefficients zones climatiques (`zone_climatique_coefficients`) → modification = revue PR avec source arrêté CEE (coefficients simplifiés tertiaire).
- Correspondance département→zone (`departement_zone_map`) → 96 départements + DOM si applicable. Ajout/modification = revue PR.

**Anti-patterns interdits** :

- Hardcoder une fiche dans un test ou un service au lieu d'étendre le YAML → refusé
- Ajouter une fiche sans `duree_vie_ans` → refusé (le moteur lèvera `ValueError`, mais la Skill bloque en amont)
- Inventer une catégorie hors des 7 canoniques → refusé

## Tests obligatoires

Toute modification touchant le CEE P6 déclenche minimum :

```bash
pytest backend/tests/ -k "cee or kwhc or cumac" -x -q     # tests métier CEE
pytest backend/tests/ -k source_guards -x -q              # 46 SG total
pytest tests/doctrine/ -x -q                              # 9 doctrine
```

Si modification de `compute_cee_kwh_cumac()` ou ajout/modification de fiche → tests de non-régression numérique sur fixtures `BAT-EN-101 + H2b + 1000m²` (kWhc cumac attendu = 50 × 1000 × 1.0 × 30 = 1 500 000), tolérance ±0.01.

**Source-guard CEE — TODO** : aucun `test_cee_source_guards.py` n'existe à ce jour dans `backend/tests/`. Les SG actuels (billing, conformite, doctrine_sol, navigation_badges) ne couvrent pas spécifiquement les anti-patterns CEE de cette Skill. **Tracking** : EPIC issue alignement Skills, task "Source-guards CEE" — créer ce fichier pour cadrer les anti-patterns Disciplines 1-5 (notamment : pas de fiche hardcodée, pas de `regulation="CEE"` non `CEE_P6`, pas de `category` invalide, formule kWhc cumac figée).

## Fichiers protégés (validation explicite avant édition)

- `backend/regops/config/cee_p6_catalog.yaml` — catalogue versionné, modification = source DGEC officielle citée
- `backend/regops/rules/cee_p6.py` (fonction `compute_cee_kwh_cumac()` et helpers) — modification = test non-régression numérique
- `backend/doctrine/constants.py` — toute nouvelle constante CEE_* = revue PR

## Triggers où cette Skill DOIT s'activer

- Édition dans `backend/regops/rules/cee_p6.py`
- Édition dans `backend/regops/config/cee_p6_catalog.yaml`
- Édition dans `backend/services/cee_service.py`
- Demande utilisateur mentionnant : CEE, fiche BAT-EN/BAT-TH/BAT-EQ/BAT-SE, kWhc cumac, MWhc, zone climatique H1a-H3, durée de vie conventionnelle, opportunité financement éco-travaux, programme P5/P6, transition P5→P6
- Ajout d'une nouvelle fiche au catalogue
- Mise à jour des coefficients zones climatiques (arrêté DGEC modificateur)

## Triggers où la Skill peut être allégée

- Documentation/commentaires uniquement
- Renommage cosmétique sans impact logique ni catalogue
- Tests purs sans modification du code testé

## Anti-patterns interdits supplémentaires (cumulatifs avec audit-then-fix)

- Hardcoder une fiche CEE en dehors de `cee_p6_catalog.yaml` → refusé
- Marquer un site "non conforme CEE" → refusé (CEE = opportunité, jamais obligation)
- Inventer un code régulation `"CEE"`, `"P6"`, `"BAT-TH"` au lieu de `"CEE_P6"` → refusé
- Modifier la formule `kWhc cumac` sans test non-régression → refusé
- Ajouter `CEE_P6` aux pondérations RegOps → refusé

## Référence croisée

- `audit-then-fix` (Skill socle, méthodo 6 phases obligatoire en amont)
- `promeos-regulatory` (expertise métier complémentaire — voir section "Relation" en haut)
- `decret-tertiaire` (cousin réglementaire — CEE P6 finance les travaux DT/BACS/APER ; activation d'une fiche CEE peut coïncider avec un Finding DT/BACS sur le même site)
- `bill-intelligence-fr` (CEE P5→P6 transitionnel : le shadow billing v4.2 traite les CEE en composante P5 implicite ELEC (~5 €/MWh, voir `billing_shadow_v2.py` section "CEE implicite") ; transition P6 à venir quand le marché P6 stabilise sa cotation)
- `regulatory_calendar` (programme P6 2026-2030 fenêtre temporelle)
- `helios_architecture` (RegOps = 1 des 6 pillars HELIOS ; CEE P6 est une rule du module RegOps)
- `docs/vision/promeos_sol_doctrine.md` (12 principes)
- `docs/dev/conventions.md` (paths canoniques, modèles Claude Code par défaut)
