---
name: bill-intelligence-fr
description: Use whenever working on French B2B electricity/gas billing logic in HELIOS — shadow billing, invoice decomposition, anomaly detection rules R01-R20, TURPE 7 + accise + CTA recalculation, billing reconciliation against measured CDC. Triggers on edits in backend/services/billing_*.py, backend/app/bill_intelligence/, or any task mentioning shadow billing, accise, CSPE, TICFE, TICGN, CTA, TURPE, billing anomalies, or invoice parsing.
---

# Bill Intelligence FR — Discipline shadow billing & décomposition facture B2B

Skill métier régulatoire. Hérite de `audit-then-fix` (méthodo socle). Cette Skill ajoute les règles spécifiques au billing B2B français : routage tarifaire, nomenclature, fichiers exemptés.

## Relation avec `promeos-billing`

Deux Skills couvrent le billing PROMEOS, avec des rôles distincts et complémentaires :

| Skill | Rôle | Triggers |
|---|---|---|
| `promeos-billing` | **Expertise métier** : connaissance régulatoire, formules CRE, structure facture B2B élec/gaz, taxonomie composants, jurisprudence tarifaire | Questions "qu'est-ce que…", "comment se calcule…", "quel est le taux 2026 de…", veille CRE/délibérations |
| `bill-intelligence-fr` (cette Skill) | **Discipline d'édition** : règles non-négociables quand on modifie le code billing (routage, nomenclature, fichiers exemptés, exigences tests) | Édition `backend/services/billing_*.py`, `backend/app/bill_intelligence/`, ajout règle R01-R20, refacto shadow billing |

**Règles de précédence** :

- Question conceptuelle régulatoire pure → `promeos-billing` répond, `bill-intelligence-fr` ne s'active pas.
- Édition de code billing → `bill-intelligence-fr` est **prioritaire et bloquant** sur le diff. `promeos-billing` peut être consulté en parallèle pour valider le fond métier d'un changement régulatoire (ex : nouveau taux CRE).
- Conflit apparent entre les deux → `bill-intelligence-fr` gagne sur la forme (où mettre la valeur, comment la nommer, comment la tester). `promeos-billing` gagne sur le fond (quelle valeur, depuis quelle source régulatoire, à partir de quelle date).

## Sources de vérité

| SoT | Rôle |
|---|---|
| `backend/doctrine/constants.py` | Constantes inviolables (CTA % part fixe TURPE) |
| `backend/config/tarifs_reglementaires.yaml` | Données tarifaires versionnées (accise élec/gaz, TURPE 7, ATRD/ATRT, CSPE/TICFE/TICGN historiques) |
| `backend/config/tarif_loader.py` | **Getters canoniques** (`get_turpe_moyen_kwh`, `get_atrd_kwh`, `get_atrt_kwh`, `get_accise_kwh`, `get_tva_normale`). Toute nouvelle accesseur tarifaire se définit ici, nulle part ailleurs. |
| `backend/services/billing_shadow_v2.py:34-48` | **Import alias** `_accise`, `_turpe`, `_atrd`, `_atrt`, `_tva` + **fallback défensif** documenté (valeurs figées si import échoue). N'est **pas** la définition canonique — c'est un alias d'usage côté services. |
| `backend/app/bill_intelligence/tariff_bridge.py` | Pont layer app (`bill_intelligence/`) vers `tarif_loader.py` / `tarifs_reglementaires.yaml` |

Toute valeur tarifaire en runtime doit transiter par l'un de ces points. Aucune autre voie.

## Discipline 1 — Routage tarifaire runtime obligatoire

**Règle** : tout calcul shadow billing, décomposition, ou réconciliation qui dépend d'une valeur tarifaire (accise, CTA, TURPE, CSPE rétro) doit passer par `_accise()` ou `tarifs_reglementaires.yaml`. Jamais de hardcoded inline.

**Fichiers concernés** :
- `backend/services/billing_canonical_service.py`
- `backend/services/billing_explainability.py`
- `backend/services/billing_reconcile.py`
- `backend/services/billing_service.py` (règles R01-R20)
- `backend/services/billing_shadow_v2.py` (moteur recalcul)
- `backend/app/bill_intelligence/engine.py`
- `backend/app/bill_intelligence/rules/`
- `backend/app/bill_intelligence/tariff_bridge.py`

**Anti-patterns interdits** :
- `accise_elec = 0.02658` en dur dans une fonction → refusé
- `cspe = 0.02100` en dur → refusé
- `cta = montant_turpe * 0.2704` → refusé (utiliser constante doctrine)
- Constante tarifaire dupliquée entre `billing_service.py` et `tariff_bridge.py` → refusé
- Ajouter un nouveau getter tarifaire ailleurs que dans `backend/config/tarif_loader.py` → refusé (drift garanti, fallback impossible à maintenir)
- Modifier le fallback défensif de `billing_shadow_v2.py:34-48` sans aligner les valeurs avec `tarif_loader.py` + `tarifs_reglementaires.yaml` → refusé (divergence silencieuse en cas d'échec import)

**Pattern correct** :

```python
# 1. Définition canonique — UNIQUEMENT dans backend/config/tarif_loader.py
def get_accise_kwh(energy: str) -> float:
    """Lit accise élec/gaz depuis tarifs_reglementaires.yaml."""
    ...

# 2. Import alias côté services — backend/services/billing_shadow_v2.py:34-48
from config.tarif_loader import get_accise_kwh as _accise

# 3. Usage côté services billing — pattern attendu partout
from backend.services.billing_shadow_v2 import _accise
accise_elec = _accise('elec')  # routé via tarif_loader → YAML
```

## Discipline 2 — Exemption explicite `billing_seed.py`

**Règle** : `backend/services/billing_seed.py` contient des **données démo HELIOS figées** (sample data pour la démo). Les valeurs hardcoded y sont **intentionnelles** — elles représentent des factures historiques fictives et ne dépendent pas de la régulation runtime.

**Conséquence** :
- Audit-then-fix Phase 1 doit reconnaître ce fichier comme exempté
- Source-guards anti-hardcoded **ne doivent pas** scanner `billing_seed.py`
- Toute modification de `billing_seed.py` reste un changement de données démo, pas un fix régulatoire
- Si une valeur de `billing_seed.py` doit refléter une régulation à jour, c'est un changement séparé tracé comme "MAJ données démo"

**Anti-pattern interdit** :
- Tagger `billing_seed.py` comme "à corriger" parce qu'il contient `cspe = 0.02100` → refusé, c'est de la donnée démo 2024 par construction

## Discipline 3 — Nomenclature accise

**Vocabulaire canonique** :

| Terme | Statut | Usage autorisé |
|---|---|---|
| **accise** sur l'électricité / le gaz | ✅ Canonique | Variables Python, fonctions, docs internes, UI principale |
| **TICFE** | ⚠️ Alias rétro-compat | Labels UI uniquement (compat user 2022+), commentaires d'alias |
| **CSPE** | ⚠️ Alias rétro-compat | Labels UI uniquement (compat user pré-2022), commentaires d'alias |
| **TICGN** | ⚠️ Alias rétro-compat | Labels UI gaz uniquement, commentaires d'alias |

**Règles strictes** :
- Noms de variables Python : **`accise_elec`, `accise_gaz`** uniquement. Jamais `cspe_*` ou `ticfe_*` ou `ticgn_*`.
- Noms de fonctions : `compute_accise(...)`, `_accise('elec')`. Jamais `compute_cspe(...)`.
- Clés YAML/JSON canoniques : `accise.elec`, `accise.gaz`. Aliases `cspe`, `ticfe`, `ticgn` admis comme clés secondaires en lecture seule pour rétro-compat.
- Labels UI utilisateur : **"Accise"** par défaut. Tooltip ou label secondaire peut mentionner "(ex-CSPE/TICFE)" pour contexte utilisateur.
- Commentaires Python : `# Accise élec (TICFE 2022-2024 / CSPE pré-2022)` autorisé pour clarté historique.

**Anti-patterns interdits** :
- `def compute_cspe_amount(...)` → refusé, renommer en `compute_accise_elec_amount`
- Variable `ticfe_rate` dans un service runtime → refusé
- Label UI principal "CSPE" sans mention "Accise" → refusé en zone produit principale

## Discipline 4 — Règles R01-R20 et explainability

`billing_service.py` contient les règles d'anomalie R01-R20 (dont R14 taxes/CSPE mismatch). Toute modification d'une règle :

- Doit préserver la traçabilité : chaque règle déclenchée produit une explication ligne par ligne via `billing_explainability.py`
- Doit avoir un test dédié dans `backend/tests/test_billing_*.py`
- Si la règle dépend d'une valeur tarifaire → routage via `_accise()` obligatoire (Discipline 1)
- Format explication user-facing : FR clair, pas de jargon non explicité

**Règle R14 spécifique** : "taxes/CSPE mismatch" — le label "CSPE" est conservé pour rétro-compat user 2022+ qui voient encore "CSPE" sur leurs anciennes factures. Le calcul interne utilise `accise_elec`. Cette dualité label/calcul est **intentionnelle**.

## Discipline 5 — Layer app vs services

Architecture à respecter :

| Layer | Path | Rôle |
|---|---|---|
| Services (legacy stable) | `backend/services/billing_*.py` | Phase 1.D close, ne pas refacto sans raison forte |
| App layer (Tier 2) | `backend/app/bill_intelligence/` | Architecture moderne, évolutions futures |

**Règle** : nouvelles features → app layer (`bill_intelligence/`). Bugs critiques sur services existants → fix en services, ne pas migrer opportunistément. Pas de duplication de logique tarifaire entre les deux layers : `tariff_bridge.py` est le pont unique.

## Tests obligatoires

Toute modification touchant le billing déclenche minimum :

```bash
pytest backend/tests/ -k billing -x -q              # tests métier billing
pytest backend/tests/test_billing_source_guards.py  # 10 SG dédiés
pytest backend/tests/ -k source_guards -x -q        # 46 SG total
pytest tests/doctrine/ -x -q                         # 9 doctrine
```

Si modification du moteur shadow billing v4.2 (`billing_shadow_v2.py`) → tests de non-régression numérique sur factures démo HELIOS (toléranace ±0.01€).

## Triggers où cette Skill DOIT s'activer

- Édition dans `backend/services/billing_*.py` (sauf `billing_seed.py` qui suit règles allégées)
- Édition dans `backend/app/bill_intelligence/`
- Demande utilisateur mentionnant : shadow billing, recalcul facture, accise, CSPE, TICFE, TICGN, CTA, TURPE, anomalie R01-R20, parsing PDF facture, réconciliation CDC vs facture
- Ajout d'un fournisseur dans `billing_normalization.py` (EDF/Engie/Total + nouveaux entrants)

## Triggers où la Skill peut être allégée

- Modification de `billing_seed.py` seul (données démo)
- Documentation/commentaires uniquement
- Renommage cosmétique sans impact logique

## Anti-patterns interdits supplémentaires (cumulatifs avec audit-then-fix)

- Ajouter une constante tarifaire en dehors de `tarifs_reglementaires.yaml` ou `doctrine/constants.py` → refusé
- Dupliquer une règle R01-R20 dans le layer app sans supprimer/déprécier dans services → refusé (drift logique garanti)
- Modifier `billing_shadow_v2.py:34-48` (getter `_accise`) sans test de non-régression numérique → refusé
- Introduire un nouveau nom de taxe en variable Python sans alignement nomenclature → refusé

## Référence croisée

- `audit-then-fix` (Skill socle, méthodo 6 phases obligatoire en amont)
- `docs/vision/promeos_sol_doctrine.md` (12 principes)
- `docs/dev/conventions.md` (paths canoniques, modèles Claude Code par défaut)
- Issue #270 (TODO labels unités frontend, peut concerner labels Accise/€/kWh affichés en UI)
