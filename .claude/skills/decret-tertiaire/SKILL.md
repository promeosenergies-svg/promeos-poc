---
name: decret-tertiaire
description: Use whenever working on French commercial-real-estate energy compliance in HELIOS — Décret Tertiaire (jalons 2030/2040/2050), BACS (Décret 2020-887, GTB), APER (parkings solaires), Audit SMÉ / ISO 50001, OPERAT (déclaration annuelle), DPE tertiaire, scoring conformité RegOps. Triggers on edits in backend/regops/, backend/services/aper_service.py, backend/services/bacs_*.py, backend/services/compliance_*.py, or any task mentioning Décret Tertiaire, jalons -40/-50/-60%, BACS classe A/B/C, OPERAT, APER, audit énergétique obligatoire, ISO 50001, valeurs absolues, modulation, exclusions.
---

# Décret Tertiaire — Discipline conformité réglementaire RegOps

Skill métier régulatoire. Hérite de `audit-then-fix` (méthodo socle). Cette Skill ajoute les règles spécifiques à la conformité énergie tertiaire France (5 régulations cumulatives) : routage constantes, nomenclature, structure rules engine, pondérations scoring.

## Relation avec `promeos-regulatory`

Deux Skills couvrent la conformité tertiaire PROMEOS, avec des rôles distincts et complémentaires :

| Skill | Rôle | Triggers |
|---|---|---|
| `promeos-regulatory` | **Expertise métier** : réglementation FR énergie tertiaire (DT/BACS/APER/Audit SMÉ/OPERAT/DPE/CSRD), seuils, sanctions, exclusions, modulation, Valeurs Absolues, jurisprudence DGEC | Questions "qu'est-ce que…", "à partir de quand…", "qui est concerné…", veille décrets/circulaires |
| `decret-tertiaire` (cette Skill) | **Discipline d'édition** : règles non-négociables quand on modifie le code RegOps (routage constantes, structure rules, pondérations scoring, exigences tests) | Édition `backend/regops/`, `backend/services/aper_service.py`, `backend/services/bacs_*.py`, `backend/services/compliance_*.py`, ajout règle `regops/rules/`, refacto scoring |

**Règles de précédence** :

- Question conceptuelle régulatoire pure → `promeos-regulatory` répond, `decret-tertiaire` ne s'active pas.
- Édition de code RegOps → `decret-tertiaire` est **prioritaire et bloquant** sur le diff. `promeos-regulatory` peut être consulté en parallèle pour valider le fond métier d'un changement (ex : nouveau seuil BACS 2030).
- Conflit apparent entre les deux → `decret-tertiaire` gagne sur la forme (où mettre la valeur, comment la nommer, comment la tester). `promeos-regulatory` gagne sur le fond (quelle valeur, depuis quel décret, à partir de quelle date).

**Pour les audits régulatoires complexes** (ajout d'une règle, refacto scoring, modification de seuil), déléguer à l'agent `regulatory-expert` via Task tool (cf. CLAUDE.md). Cette Skill cadre les règles d'édition ; `regulatory-expert` exécute les tâches lourdes avec validation métier.

## Sources de vérité

| SoT | Rôle |
|---|---|
| `backend/doctrine/constants.py` | **Constantes inviolables** réglementaires (DT_MILESTONES, DT_PENALTY_EUR, BACS_PENALTY_EUR, APER_*, AUDIT_SME_*, OPERAT_PENALTY_EUR, REGOPS_WEIGHTS_*). Modification = revue PR avec source officielle décret/circulaire. |
| `backend/regops/config/regs.yaml` | Configuration rules par régulation (seuils déclenchement, métadonnées, applicability flags) |
| `backend/regops/config/scoring_profile.json` | Profil scoring conformité (pondérations runtime, fallbacks) |
| `backend/regops/config/legal_refs.py` | Références légales canoniques (codes décrets, articles, dates JO) — citation obligatoire dans rules |
| `backend/regops/rules/*.py` | **Rules engine** (tertiaire_operat.py, bacs.py, aper.py, dpe_tertiaire.py, cee_p6.py). Chaque règle produit un `Finding` avec `regulation`, `rule_id`, `inputs_used`, `explanation`. |
| `backend/regops/scoring.py` | **SoT scoring conformité** RegOps. Modifier uniquement avec validation explicite. |
| `backend/services/compliance_score_service.py` | Service de scoring exposé API (consomme regops/scoring.py) |

Toute valeur réglementaire en runtime doit transiter par l'un de ces points. Aucune autre voie.

## Discipline 1 — Routage constantes obligatoire

**Règle** : tout calcul, scoring, ou affichage qui dépend d'une valeur réglementaire (jalon DT, pénalité, seuil BACS/APER/Audit SMÉ, deadline) doit passer par `backend/doctrine/constants.py`. Jamais de hardcoded inline en service ou route.

**Anti-patterns interdits** :

- `penalty = 7500` en dur dans une fonction → refusé (utiliser `DT_PENALTY_EUR`)
- `if site.surface_parking > 1500:` en dur → refusé (utiliser `APER_PARKING_MIN_SURFACE_M2`)
- `milestones = {2030: 0.40, 2040: 0.50, 2050: 0.60}` en dur frontend ou backend → refusé (utiliser `DT_MILESTONES`, route via API)
- Constante répliquée entre `aper_service.py` et `regs.yaml` sans synchronisation → refusé (drift garanti)
- Ajouter une nouvelle constante réglementaire ailleurs que dans `backend/doctrine/constants.py` → refusé

**Pattern correct** :

```python
# 1. Définition canonique — backend/doctrine/constants.py
DT_PENALTY_EUR = 7500
DT_PENALTY_AT_RISK_EUR = 3750
DT_MILESTONES = {2030: -0.40, 2040: -0.50, 2050: -0.60}

# 2. Usage côté services / rules
from backend.doctrine.constants import DT_PENALTY_EUR, DT_MILESTONES
penalty = DT_PENALTY_EUR
target_2030 = DT_MILESTONES[2030]
```

## Discipline 2 — Nomenclature canonique 5 régulations

**Vocabulaire canonique** (codes utilisés dans `Finding.regulation`, scoring, API) :

| Code canonique | Régulation | Anti-pattern interdit |
|---|---|---|
| `DT` ou `TERTIAIRE_OPERAT` | Décret Tertiaire (Décret 2019-771) | "decret_tertiaire", "EcoEnergieT" libre |
| `BACS` | Bâtiments Automation Control Systems (Décret 2020-887) | "GTB" en code (label UI uniquement) |
| `APER` | Loi 2023-175 art. 40 + Décret 2022-1726 (parkings solaires) | "loi_aper", "solar_parking" |
| `AUDIT` ou `AUDIT_SME` | Audit Énergétique Obligatoire / ISO 50001 | "audit_obligatoire", "ISO50001" en clé |
| `OPERAT` | Déclaration annuelle DT (plateforme ADEME) | "declaration_operat" en clé code |

**Règles strictes** :

- Code interne `regulation` dans `Finding`, `rule_id`, scoring → **codes canoniques majuscules** uniquement (`DT`, `BACS`, `APER`, `AUDIT`, `OPERAT`).
- Variables Python : `dt_score`, `bacs_compliance`, `aper_status`, `audit_sme_threshold`. Jamais `decretTertiaire`, `gtbScore`.
- Labels UI utilisateur : "Décret Tertiaire", "BACS / GTB", "APER (parkings solaires)", "Audit énergétique", "OPERAT" — formes humaines acceptables, mais clés techniques restent canoniques.
- Pas d'invention de nouveaux codes (`SMARTBUILDING`, `DPE_PRO`, etc.) sans validation explicite — chaque code = un décret réel cité dans `legal_refs.py`.

## Discipline 3 — Décret Tertiaire : jalons 2030/2040/2050 uniquement

**Règle critique** (tracée explicitement en commentaire à côté de `DT_MILESTONES` dans `backend/doctrine/constants.py`) :

> IMPORTANT : aucun jalon 2026. Les jalons réglementaires sont 2030/2040/2050.

**Conséquence** :

- Toute logique conditionnelle "si année ≥ 2026" liée au DT → refusée. Le DT ne déclenche aucun palier en 2026.
- Toute alerte UI "Vous êtes hors jalon 2026" → refusée. Le bon message est "Vous êtes en trajectoire / hors trajectoire vers 2030".
- Année de référence par défaut = `DT_REF_YEAR_DEFAULT = 2020`. Modulations possibles (sites neufs, exclusions, valeurs absolues sectorielles) → traitées par `regops/rules/` pas en dur.
- La pénalité DT (`DT_PENALTY_EUR = 7500`) s'applique **par site** non conforme **après** échéance officielle (2030, 2040, 2050). La pénalité "at risk" (`DT_PENALTY_AT_RISK_EUR = 3750`) signale un site qui dévie de la trajectoire — **calcul interne**, pas une sanction réelle déjà encourue.

**Anti-patterns interdits** :

- Hardcoder un jalon 2026 dans `regops/rules/tertiaire_operat.py` → refusé.
- Utiliser `DT_PENALTY_AT_RISK_EUR` comme s'il s'agissait d'une vraie sanction encourue → refusé (jamais en label UI "vous devez 3 750 €").
- Modifier `DT_MILESTONES` sans citation source officielle (Décret 2019-771 ou décret modificateur) → refusé.

## Discipline 4 — Structure rules engine + explainability `regops/rules/`

**Règle** : chaque règle d'une régulation suit le format `Finding`-producer commun à `tertiaire_operat.py`, `bacs.py`, `aper.py`, `dpe_tertiaire.py`, `cee_p6.py`.

> Note : `cee_p6.py` est listée ici pour exhaustivité du rules engine, mais les disciplines spécifiques CEE P6 (catalogue fiches BAT-TH-*, kWhc cumac, période 2026-2030) sont couvertes par la Skill `cee-p6` (Skill 4/4 de la série).

**Format obligatoire** d'un `Finding` produit :

```python
Finding(
    regulation="BACS",                    # code canonique majuscules
    rule_id="BACS_THRESHOLD_NOT_MET",     # snake majuscules, unique par régulation
    severity="critical|warning|info",
    site_id=site.id,
    deadline=...,                          # date butoir réglementaire
    trigger_condition="puissance_chauffage_kw < BACS_THRESHOLD_KW",
    inputs_used=["puissance_chauffage_kw", "surface_m2"],
    explanation="...",                     # FR clair user-facing
    legal_ref="Décret 2020-887 art. R.175-2",  # citation legal_refs.py
)
```

**Règles strictes** :

- Pas de logique scoring dans les rules → les rules produisent des `Finding`, le scoring agrège dans `regops/scoring.py`.
- Pas de logique d'I/O DB dans les rules → input = objet site/portfolio résolu en amont, output = liste `Finding`.
- `inputs_used` exhaustif → traçabilité explainability (voir bloc ci-dessous).
- `legal_ref` obligatoire → cite le décret/article/circulaire depuis `legal_refs.py`.
- Une nouvelle règle = un nouveau `rule_id` unique. Pas de mutation silencieuse d'un `rule_id` existant (cassage des bases d'audit historiques).

**Explainability obligatoire** — chaque `Finding` doit pouvoir être expliqué à l'utilisateur final (DAF, Resp. Conformité, EM, Auditeur) :

- `explanation` : phrase FR user-facing qui dit **pourquoi** la règle s'est déclenchée et **quel** est le palier réglementaire.
- `inputs_used` : liste exhaustive des champs site/bâtiment qui ont déclenché la règle. Permet à l'UI de naviguer "voir les données utilisées".
- `legal_ref` : référence officielle citable. Permet à l'auditeur de remonter au texte source.

**Anti-patterns interdits** :

- `explanation = "Site non conforme"` sans précision → refusé (jargon non explicité, pas user-facing). Écrire plutôt : `"Puissance chauffage installée 75 kW ≥ seuil BACS 70 kW. Système GTB classe A/B obligatoire avant le 01/01/2030 (Décret 2020-887)."`
- `inputs_used = []` → refusé (cassage chain explainability frontend, l'UI ne peut pas afficher "voir les données").

## Discipline 5 — Pondérations scoring : 2 profils, pas un de plus

**Règle** : le scoring conformité agrège DT + BACS + APER + AUDIT selon **2 profils canoniques** définis dans `backend/doctrine/constants.py` (`REGOPS_WEIGHTS_AUDIT_APPLICABLE` + `REGOPS_WEIGHTS_DEFAULT`) :

```python
REGOPS_WEIGHTS_AUDIT_APPLICABLE = {"DT": 0.39, "BACS": 0.28, "APER": 0.17, "AUDIT": 0.16}
REGOPS_WEIGHTS_DEFAULT = {"DT": 0.45, "BACS": 0.30, "APER": 0.25}
```

- `AUDIT_APPLICABLE` → site ≥ 2,75 GWh consommation finale (audit énergétique obligatoire ou ISO 50001).
- `DEFAULT` → site < 2,75 GWh, pas d'audit applicable.

**Règles strictes** :

- Les 4 (ou 3) clés somment à 1.0 ± epsilon. Toute redistribution doit préserver cette propriété.
- Modifier les pondérations → revue PR avec justification (audit DGEC, retour terrain pilote).
- Pas de 3ᵉ profil (`PARTIAL_AUDIT`, `LIGHT`, etc.) sans validation explicite — les 2 profils couvrent le périmètre légal complet.
- `OPERAT` n'apparaît pas dans les pondérations → c'est une obligation déclarative séparée (pénalité via constante `OPERAT_PENALTY_EUR` dans `backend/doctrine/constants.py` ; consulter le fichier pour la valeur courante et sa source citée), pas une dimension de scoring DT.

**Anti-patterns interdits** :

- `weights = {"DT": 0.5, "BACS": 0.3, "APER": 0.2}` en dur dans un service → refusé (utiliser `REGOPS_WEIGHTS_DEFAULT`)
- Ajouter "DPE" comme dimension de scoring DT → refusé (DPE = règle séparée `dpe_tertiaire.py`, pas pondérée dans le score conformité tertiaire)

## Tests obligatoires

Toute modification touchant la conformité déclenche minimum :

```bash
pytest backend/tests/ -k "regops or bacs or aper or audit_sme or operat or conformite" -x -q
pytest backend/tests/test_conformite_source_guards.py     # SG conformité dédiés
pytest backend/tests/test_regops_rules.py                 # rules engine
pytest backend/tests/ -k source_guards -x -q              # 46 SG total
pytest tests/doctrine/ -x -q                              # 9 doctrine
```

Si modification de `regops/scoring.py` ou des pondérations → tests de non-régression numérique sur sites démo HELIOS (tolérance ±0.001 sur score).

## Fichiers protégés (validation explicite avant édition)

- `backend/doctrine/constants.py` — toute modification réglementaire = revue PR + source officielle citée
- `backend/regops/scoring.py` — SoT scoring, modification = test non-régression numérique obligatoire
- `backend/regops/config/regs.yaml` — config rules versionnée
- `backend/regops/config/scoring_profile.json` — profil runtime
- `backend/regops/config/legal_refs.py` — citations officielles

## Triggers où cette Skill DOIT s'activer

- Édition dans `backend/regops/` (rules, engine, scoring, completeness, data_quality)
- Édition dans `backend/services/aper_service.py`, `backend/services/bacs_*.py`, `backend/services/compliance_*.py`
- Demande utilisateur mentionnant : Décret Tertiaire, jalons -40/-50/-60%, BACS classe A/B/C, GTB, OPERAT, APER, parking solaire, audit énergétique obligatoire, ISO 50001, valeurs absolues, modulation, exclusions, scoring conformité
- Ajout d'une règle dans `regops/rules/`
- Modification d'une pondération scoring

## Triggers où la Skill peut être allégée

- Documentation/commentaires uniquement
- Renommage cosmétique sans impact logique ni constante
- Tests purs sans modification de la rule testée

## Anti-patterns interdits supplémentaires (cumulatifs avec audit-then-fix)

- Ajouter une constante réglementaire en dehors de `backend/doctrine/constants.py` → refusé
- Inventer un code `regulation` non listé dans Discipline 2 → refusé
- Utiliser un jalon DT 2026 (n'existe pas) → refusé
- Modifier les pondérations RegOps sans test non-régression numérique → refusé
- Produire un `Finding` sans `legal_ref` ou avec `inputs_used = []` → refusé
- Dupliquer une règle entre `regops/rules/` et un service → refusé (drift logique garanti)

## Référence croisée

- `audit-then-fix` (Skill socle, méthodo 6 phases obligatoire en amont)
- `promeos-regulatory` (expertise métier complémentaire — voir section "Relation" en haut)
- `regops_constants` (skill canonique wrappant les règles `regops/rules/`)
- `regulatory_calendar` (deadlines 2026-2050 : OPERAT annuel, Audit SMÉ 2026-10-11, APER 2028-01-01, DT 2030/2040/2050, BACS 2030 abaissement seuil)
- `helios_architecture` (RegOps = 1 des 6 pillars HELIOS ; positionnement architecture cross-modules)
- `docs/vision/promeos_sol_doctrine.md` (12 principes)
- `docs/dev/conventions.md` (paths canoniques, modèles Claude Code par défaut)
