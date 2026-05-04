# ADR-009 — Séparation namespace `/api/config/*` vs `/api/regulatory/*`

**Statut** : Draft (validation Sprint C-4 amont)
**Date** : 2026-05-04
**Sprint** : C-4 amont (Phase 0)
**Personnes impliquées** : Amine (founder), Claude architect-helios
**Tracking dette** : `D-Sprint-C3-7d-ADR-Routes-Namespace-001`

---

## Contexte

Sprint C-3 Phase 3.3 a livré `GET /api/regulatory/rates` (endpoint public sources légales tracées). Audit Phase 0 Sprint C-4 dénombre :

### Routers actuels `/api/config/*`

| Fichier | Endpoints | Sémantique |
|---|---|---|
| `routes/config_emission_factors.py` | `GET /api/config/emission-factors` | Constantes Python `config/emission_factors.py` (CO₂ ADEME V23.6) |
| `routes/config_price_references.py` | `GET /api/config/price-references` | Heuristiques pricing marché (`pricing_lead_score.yaml`) |
| `routes/config_regulatory_constants.py` | `GET /api/config/regulatory-constants` | Constantes Python `regops/constants.py` (seuils OPERAT/BACS/APER) |

### Routers actuels `/api/regulatory/*`

| Fichier | Endpoints | Sémantique |
|---|---|---|
| `routes/regulatory_rates.py` | `GET /api/regulatory/rates` | Sources légales tracées YAML `sources_reglementaires.yaml` (68 termes / 11 domaines + version + JORFTEXT + URL deep-link) |

**Risque sans ADR** : ambiguïté future sur où poser un nouveau endpoint. Exemple :
- `GET /api/regulatory/constants` ? (vs `/api/config/regulatory-constants` actuel)
- `GET /api/config/rates` ? (vs `/api/regulatory/rates` actuel)

---

## Décision

### Règle de routage cardinale

| Namespace | Sémantique stricte | Type de données |
|---|---|---|
| **`/api/config/*`** | Constantes Python runtime (figées en code, pas de traçabilité légale exigée par la consommation FE) | `emission_factors.py`, `regops/constants.py`, heuristiques `pricing_lead_score.yaml` |
| **`/api/regulatory/*`** | **Sources légales tracées** (YAML versionné git, traçabilité Légifrance/CRE/RTE/ADEME exigée — base TraceTooltip R10) | `sources_reglementaires.yaml` (68 termes / 11 domaines + JORFTEXT + URL deep-link), futurs : ELD gaz, ATRT8 grilles, capacité 2026 |

### Critère de décision (matrice)

Pour décider où poser un nouveau endpoint, répondre à 2 questions :

1. **Le FE doit-il afficher la source légale (TraceTooltip) ?** (JORFTEXT + version + date + URL)
   - **Oui** → `/api/regulatory/*`
   - **Non** → `/api/config/*`

2. **La donnée est-elle versionnée git avec doctrine PROMEOS de traçabilité réglementaire ?** (YAML SoT vs constantes Python figées)
   - **YAML versionné + traçabilité** → `/api/regulatory/*`
   - **Python figé OU heuristique métier** → `/api/config/*`

**Cohérence** : les deux questions doivent converger vers le même namespace. Si divergence → réviser l'ADR avant ajout.

### Cas concrets

| Endpoint | Namespace cible | Justification |
|---|---|---|
| TURPE 7 grilles (CRE délibération 2024-12-19) | `/api/regulatory/turpe` | Source légale tracée + TraceTooltip |
| Accises élec/gaz 2026 (LFI) | `/api/regulatory/rates` (existant) | Source légale tracée + TraceTooltip |
| ELD gaz référentiel (CRE liste officielle) | `/api/regulatory/eld-gaz` | Source légale tracée + TraceTooltip |
| Émission factor élec ADEME V23.6 | `/api/config/emission-factors` (existant) | Constante Python figée, déjà branchée FE sans TraceTooltip |
| Heuristique pricing lead score | `/api/config/price-references` (existant) | Heuristique métier, pas de source légale |
| Seuils OPERAT/BACS/APER (Décret 2019-771 etc.) | `/api/config/regulatory-constants` (existant) | **À migrer Sprint C-7** vers `/api/regulatory/*` (source légale + traçabilité requise FE) |

### Migration recommandée Sprint C-7

`/api/config/regulatory-constants` est ambigu : son nom contient "regulatory" mais il vit sous `/api/config/*`. Ses données (seuils OPERAT 1000m², BACS 290kW/70kW, APER 500m², dates DT 2030/2040/2050) sont des **sources légales tracées** (Décret 2019-771, Décret 2020-887, Loi APER 2023-175).

→ **Migration Sprint C-7** : `/api/config/regulatory-constants` → `/api/regulatory/constants` (alias backward-compat 6 mois). Conditions :
- Migration des consumers FE (TraceTooltip à activer)
- Source-guard cohérence YAML ↔ `regops/constants.py` étendu (cf. `D-Sprint-C3-YAML-Constants-SG-Coverage-001`)
- ADR mise à jour confirmant migration

### Doctrine source-guards

Source-guard à ajouter Sprint C-4 P4.5 : `test_routes_namespace_doctrine_source_guards.py`
- SG_NAMESPACE_01 : tout fichier `routes/regulatory_*.py` doit lire depuis YAML versionné (`sources_reglementaires.yaml` ou cohérent)
- SG_NAMESPACE_02 : tout fichier `routes/config_*.py` ne doit PAS exposer de champ `legal_reference`/`jorftext`/`source_url` (sinon → migrer vers `/api/regulatory/*`)
- SG_NAMESPACE_03 : pas de duplication endpoint cross-namespace (ex : interdire `/api/config/rates` et `/api/regulatory/rates` simultanément)

---

## Conséquences

### Positives

- **Lisibilité API** : namespace = sémantique immédiatement claire (config vs source légale tracée)
- **Différenciateur R10 préservé** : tout endpoint `/api/regulatory/*` est candidat TraceTooltip natif
- **Cohérence migration future** : règle explicite pour Sprint C-7 + suivants
- **Source-guards anti-dérive** : pattern violations bloquées au commit

### Négatives / Compromis

- **Migration `/api/config/regulatory-constants`** = breaking change futur (Sprint C-7) → période transition 6 mois alias
  - Mitigation : alias backward-compat + Swagger doc
- **Coût cognitif** initial : devs doivent connaître la matrice de décision
  - Mitigation : ADR-009 cité dans CONTRIBUTING.md + commentaire en haut de chaque router
- **Risque sur-classification** : tout endpoint avec un chiffre réglementaire est-il sous `/api/regulatory/*` ?
  - Réponse : **uniquement si traçabilité TraceTooltip exigée FE** (cf. matrice 2 questions ci-dessus)

### Tests anti-régression Sprint C-4

- 1 test `routes/regulatory_*.py` lit YAML versionné (pas de constante Python inline)
- 1 test `routes/config_*.py` ne expose pas champ `legal_reference`
- 1 test pas de duplication endpoint cross-namespace

---

## Alternatives considérées

| Option | Pourquoi rejetée |
|---|---|
| **Tout sous `/api/config/*`** (statu quo + ne pas créer `/api/regulatory/*`) | Perd le différenciateur R10. TraceTooltip implique sémantique légale tracée distincte. |
| **Tout sous `/api/regulatory/*`** | Sur-classifie les heuristiques marché (`pricing_lead_score`) qui ne sont pas des sources légales. |
| **Préfixe par domaine** : `/api/operat/*`, `/api/turpe/*`, `/api/co2/*` | Multiplication des préfixes, casse cohérence cross-pillar. Doctrine PROMEOS = pillars cross-cutting (Bill, RegOps, EMS, Achat, etc.) — namespace technique > pillar. |
| **Versionning explicite** : `/api/v1/regulatory/*` vs `/api/v2/regulatory/*` | Pas de v2 prévue, prématuré. À considérer Sprint C-7+ si breaking change majeur. |
| **Migration immédiate Sprint C-4** de `/api/config/regulatory-constants` | Scope creep Sprint C-4 (FE consumers à migrer + tests à adapter). Reporter Sprint C-7 polish. |

---

## Statut & validation

- **Draft** : 2026-05-04 (Sprint C-4 amont)
- **Validation requise** : architect-helios
- **Implémentation Sprint C-4 P4.5** :
  - Source-guards namespace doctrine
  - Documentation CONTRIBUTING.md + commentaires routers
  - Pas de migration `/api/config/regulatory-constants` ce sprint (reporté C-7)

Closes (post-implémentation) : `D-Sprint-C3-7d-ADR-Routes-Namespace-001`.
