# OPERAT Source Trust — Meteo, Actor, Baseline Policy

> Date : 2026-03-16
> Commit : `225d612`
> Statut : Implemente, teste, pushe

---

## Fichiers crees

| Fichier | Role |
|---------|------|
| `backend/services/weather_provider.py` | Connecteur meteo leger (DJU par zone climatique) |
| `backend/services/actor_resolver.py` | Resolution identite actor (email > user_id > header > fallback) |
| `backend/tests/test_source_trust.py` | 15 tests (meteo 6, actor 4, baseline 4, weather 1) |

## Fichiers modifies

| Fichier | Modification |
|---------|-------------|
| `backend/models/tertiaire.py` | +baseline_normalization_status, +baseline_normalization_reason |
| `backend/database/migrations.py` | Migration 2 colonnes |
| `backend/services/operat_trajectory.py` | Baseline policy + weather_provider dans reponse |
| `backend/services/operat_normalization.py` | Audit-trail normalisation |
| `backend/routes/tertiaire.py` | +auto-normalize endpoint avec weather provider |
| `frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx` | Badges baseline status + weather provider |

---

## Weather Provider

| Source | Provider | Verified | Confidence |
|--------|----------|----------|-----------|
| Table RT2012 interne | promeos_reference_table | true | medium |
| Saisie manuelle | manual | **false** | **low** |
| API Meteo-France (futur) | meteo_france | true | high |

Zones climatiques :
- H1 : Nord, Est, IDF (DJU ref ~2600)
- H2 : Ouest, Centre (DJU ref ~2200)
- H3 : Mediterranee (DJU ref ~1600)

Mapping : code postal (2 premiers chiffres) → zone

---

## Actor Resolver

| Priorite | Source | Exemple |
|----------|--------|---------|
| 1 | auth.email | user@company.com |
| 2 | auth.user_id | user_42 |
| 3 | Header X-Actor | api_bot |
| 4 | Fallback | manual_unknown |

**Actor JAMAIS vide.** Fallback explicite si non identifie.

---

## Baseline Normalization Policy

| Status | Signification | Impact |
|--------|--------------|--------|
| normalized | Baseline normalisee DJU | Comparaison coherente |
| raw_only | Baseline brute (DJU absents) | Warning base mixte |
| not_possible | Baseline absente | not_evaluable |
| unknown | Non determine | Warning |

Expose dans :
- `validate` response : `baseline.normalization_status`, `baseline_normalization_reason`
- TertiaireEfa model : cache pour performances
- UI : badge Normalisee / Brute / Non normalisable

---

## Endpoint auto-normalize

```
POST /api/tertiaire/efa/{id}/consumption/auto-normalize
{
  "consumption_id": 42,
  "code_postal": "75001"  // optionnel, resolu depuis le site
}
```

Retour enrichi :
```json
{
  "raw_kwh": 300000,
  "normalized_kwh": 330000,
  "weather": {
    "provider": "promeos_reference_table",
    "source_ref": "RT2012_zone_H1_2025",
    "source_verified": true,
    "climate_zone": "H1",
    "confidence": "medium"
  },
  "actor": "user@company.com"
}
```

---

## Tests (15 passes)

| Test | Verifie |
|------|---------|
| auto_source_is_verified | Source table = verified |
| manual_override_not_verified | Override = non verifie |
| zone_detection_paris | H1 |
| zone_detection_marseille | H3 |
| zone_detection_nantes | H2 |
| dju_reference_positive | DJU > 0 |
| actor_never_empty | Fallback marche |
| actor_fallback | manual_unknown |
| actor_auth_email | Email prioritaire |
| actor_header | X-Actor header |
| baseline_raw_only_status | raw_only si non normalise |
| baseline_normalized_status | normalized si normalise |
| no_optimistic_final_when_baseline_raw | Pas d'optimisme injustifie |
| weather_provider_in_response | Provider expose |

---

## Bilan conformite OPERAT complet

| Brique | Commit | Tests |
|--------|--------|-------|
| Securite labels + wording | `fc6de2d` | 16 |
| Socle trajectoire | `7b604bd` | 16 |
| Audit-trail + qualification source | `ff9a7b4` | 14 |
| Chaine de preuve export | `4ca8650` | 8 |
| Normalisation climatique DJU | `a235ea3` | 8 |
| Gouvernance statut final | `85cf130` | 9 |
| **Source trust (meteo + actor + baseline)** | **`225d612`** | **15** |
| **Total** | **7 commits** | **86 tests** |

---

## Limites restantes

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| DJU estimes (pas API Meteo-France reelle) | Approximation | Table RT2012 = source verifiee interne, confidence medium |
| Actor souvent manual_unknown si pas d'auth | Tracabilite partielle | Quand IAM branche, actor sera reel |
| Pas de signature numerique | Export non certifie | Checksum SHA-256 present |
| Pas de depot reel OPERAT | Simulation par design | Labels explicites |
