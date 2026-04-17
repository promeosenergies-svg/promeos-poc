# KB Governance — Regles de curation et lifecycle

## Lifecycle des items KB

```
draft -> validated -> deprecated
              |
         under_review (via FeedbackDigestAgent si FP > 60%)
```

## Regles

1. **validated + confidence=low** est INTERDIT (hard rule)
2. Seuls les items `validated` sont utilises par les agents IA (default)
3. Les items `draft` sont visibles en mode exploration uniquement
4. La transition `under_review` est automatique si FP rate > 60% sur 3+ annotations

## Ownership par namespace

| Namespace | Owner | Validation |
|-----------|-------|-----------|
| constants | regulatory | Obligatoire (SME) |
| regulations | regulatory | Obligatoire (SME) |
| archetypes | analytics | Obligatoire |
| anomaly_rules | analytics | Auto-curation possible |
| recommendations | product | Auto-curation possible |
| market_intel | market | Non requise |

## Annotation workflow

1. Un objet (insight, anomaly, kb_item) est cree
2. RouterAgent decide qui doit annoter (humain ou auto)
3. L'annotation est creee (label + confidence + provenance)
4. ProfilerAgent recalcule le trust_weight de l'annotateur
5. FeedbackDigestAgent verifie les FP rates et flag les regles

## Sources de verite

- Constantes : `config/emission_factors.py` + `config/tarifs_reglementaires.yaml`
- Items KB : `backend/data/kb.db` (app/kb/ engine)
- Annotations : `backend/data/promeos.db` (table annotations)
- Skills : `.claude/skills/promeos-constants/SKILL.md` (genere par kb_export_skills.py)
