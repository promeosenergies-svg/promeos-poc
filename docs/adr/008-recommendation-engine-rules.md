# ADR-008: Recommendation Engine — Règles métier hardcodées

**Date**: 2026-04-12
**Statut**: Accepted
**Sprint**: Sprint 7 — Push vers le 10

---

## Contexte

Les services analytiques PROMEOS (load_profile, energy_signature, enedis_benchmarks) calculent une quinzaine de KPIs (baseload, load factor, thermosensibilite, score d'atypie, etc.). Mais ces KPIs en eux-memes ne sont pas des actions : l'utilisateur voit des chiffres, pas des recommandations.

Le modele DB `Recommendation` existe depuis longtemps, avec ICE scoring (Impact/Confidence/Ease), mais aucun code ne transforme les KPIs en objets `Recommendation`.

---

## Probleme

Comment transformer les KPIs analytiques en `Recommendation` objects persistes, avec ICE scoring et priorisation ?

Options :

### Option A: Knowledge Base (KB) + regles YAML/DB

- (+) Configurable sans redeploiement
- (+) Auditable, versionnable
- (-) Sur-engineering pour un POC : necessite loader, parser, validator
- (-) Les regles metier sont stables (on ne les change pas toutes les semaines)
- (-) PROMEOS a deja une architecture KB mais elle n'est pas wired pour les recommandations

### Option B: Moteur de regles generique (Drools, Camunda DMN)

- (+) Standard, industriel
- (-) Ecrasant pour 6 regles
- (-) Dependance externe

### Option C: Fonctions Python pures (choisi)

- 1 fonction par regle, prenant un KPI dict en entree, retournant `(Anomaly_dict, Recommendation_dict)` ou `None`
- Une liste `_RULES` qui orchestre l'application
- Un dispatcher `generate_recommendations_for_site(db, site_id)` qui collecte les analytics et applique les regles

---

## Decision

**Option C : Rules as pure Python functions.**

### Architecture

```python
# backend/services/recommendation_engine.py

def _rule_baseload_excessive(load_profile: dict, meter_id: int) -> tuple[dict, dict] | None:
    if load_profile["baseload"]["verdict"] != "eleve": return None
    if load_profile["baseload"]["baseload_pct_of_mean"] < 60: return None
    return (anomaly_dict, recommendation_dict)

_RULES = [
    ("load_profile", _rule_baseload_excessive),
    ("load_profile", _rule_low_load_factor),
    ("load_profile", _rule_night_day_ratio_high),
    ("load_profile", _rule_data_quality_low),
    ("signature", _rule_thermosensitivity_high),
    ("benchmark", _rule_atypicity_high),
]

def generate_recommendations_for_site(db, site_id, persist=True):
    analytics = {
        "load_profile": compute_load_profile(db, site_id),
        "signature": compute_energy_signature_advanced(db, site_id),
        "benchmark": compute_benchmark(db, site_id),
    }
    generated = []
    for source_key, rule_fn in _RULES:
        result = rule_fn(analytics[source_key], meter_id)
        if result:
            generated.append(result)
    # Trier par ICE, persister dans Anomaly + Recommendation tables
    ...
```

### Regles implementees (Sprint 7)

| Regle | Seuil | Severity | ICE typique |
|---|---|---|---|
| Baseload excessive | pct > 60% | high | 7.9 (9/8/7) |
| Load factor faible | LF < 0.15 | medium | 7.6 (7/7/9) |
| Ratio nuit/jour eleve | > 0.5 | high | 6.9 (8/7/6) |
| Thermosensibilite elevee | part > 40% + heating | medium | 5.8 (8/6/4) |
| Atypie sectorielle | score > 0.50 | medium | 5.9 (6/5/7) |
| Qualite donnees faible | score < 0.80 | low | 5.9 (3/10/9) |

### ICE scoring : moyenne geometrique (pas produit)

```python
def _ice(impact: int, confidence: int, ease: int) -> float:
    return round((impact * confidence * ease) ** (1 / 3), 2)
```

Rationale : la moyenne geometrique penalise fortement les dimensions faibles (ex. facilite = 2 tire le score vers le bas), alors que le produit brut explose les scores hauts (10 * 10 * 10 = 1000 vs 5 * 5 * 5 = 125, ratio 8x pour une variation lineaire 2x).

---

## Consequences

### Positives

- **Testable** : 22 tests unitaires (`test_recommendation_engine.py`), 1 test par regle + pipeline complet
- **Debuggable** : stack trace claire, pas de moteur opaque
- **Rapide a iterer** : ajouter une regle = ecrire 20 lignes Python
- **ICE transparent** : formule claire, tests explicites
- **Persistance immediate** : les recommandations apparaissent dans la table `recommendation` existante, donc dans l'inbox cockpit sans frontend additionnel

### Negatives

- **Pas reconfigurable sans redeploiement** : si les seuils changent (ex. baseload > 70% au lieu de 60%), il faut un commit
- **Pas d'audit trail** : pas de log "telle regle a ete declenchee par telles valeurs"
- **Pas de KB integration** : la traceabilite `kb_rule_id` dans le modele Anomaly n'est pas utilisee
- **Pas d'explicabilite multi-factor** : chaque regle decide en isolation, pas de regle composite

### Migration future

Si le besoin se presente :
- Extraire les seuils dans `config/recommendation_thresholds.yaml`
- Ajouter un `RuleKbEntry` model pour versioner les regles
- Wrapper les fonctions dans un `Rule` class avec metadata

---

## References

- Fichier : `backend/services/recommendation_engine.py`
- Tests : `backend/tests/test_recommendation_engine.py` (22 tests)
- Modeles DB : `Anomaly`, `Recommendation` dans `backend/models/energy_models.py`
- Endpoint : `POST /api/usages/recommendations/generate/{site_id}`
