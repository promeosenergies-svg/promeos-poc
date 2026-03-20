# OPERAT Normalisation climatique DJU

> Date : 2026-03-16
> Commit : `a235ea3`
> Statut : Implemente, teste, pushe

---

## Methode

**DJU (Degres-Jours Unifies)** :

```
conso_normalisee = conso_brute * (DJU_reference / DJU_observe)
```

- DJU_reference = moyenne 30 ans (norme)
- DJU_observe = DJU de l'annee en cours
- Si DJU absents : pas de normalisation, warning explicite

**La valeur brute n'est JAMAIS ecrasee.** Les deux valeurs coexistent.

---

## Confiance

| Ecart DJU | Confiance |
|-----------|-----------|
| <= 5% | high |
| 5-15% | medium |
| > 15% | low + warning |

---

## Champs ajoutes sur TertiaireEfaConsumption

```
normalized_kwh_total, normalization_method, normalization_confidence,
dju_heating, dju_cooling, dju_reference, weather_data_source, normalized_at
```

---

## Trajectoire enrichie

L'endpoint `/targets/validate` retourne maintenant :

```json
{
  "raw_status": "off_track",
  "normalized_status": "on_track",
  "raw_delta_kwh": 20000,
  "normalized_delta_kwh": -8000,
  "normalization": {
    "applied": true,
    "method": "dju_ratio",
    "confidence": "medium",
    "weather_source": "meteo_france",
    "dju_heating": 2000,
    "dju_reference": 2200
  },
  "status": "on_track",
  "warnings": []
}
```

Le `status` final utilise la version normalisee si disponible, sinon la brute.

---

## Endpoints

| Methode | Path | Role |
|---------|------|------|
| POST | `/api/tertiaire/efa/{id}/consumption/normalize` | Normaliser une conso (DJU) |
| GET | `/api/tertiaire/efa/{id}/normalization-history` | Historique normalisation |

---

## UI

Le bloc trajectoire affiche maintenant :

```
Reference                     Observation 2026
500 000 kWh (2019)            320 000 kWh (brute)
[Fiable] factures             352 000 kWh (normalisee)
                              [Fiable] factures
                              [dju_ratio · medium]

Objectif 2030 : 300 000 kWh   +20 000 kWh brut
Ecart normalise               +52 000 kWh (+17.3%)
```

---

## Tests (8 passes)

| Test | Verifie |
|------|---------|
| dju_ratio_correct | Calcul 300k * 2200/2000 = 330k |
| raw_never_overwritten | kwh_total intacte apres normalisation |
| no_normalization_if_no_dju | Warning explicite, method=none |
| confidence_high_small_ecart | Ecart <= 5% |
| confidence_low_big_ecart | Ecart > 15% + warning |
| trajectory_shows_both | raw_status + normalized_status |
| trajectory_warning_not_normalized | Warning "brutes non normalisees" |
| history_returns_all_years | Historique complet |

---

## Bilan conformite OPERAT complet

| Brique | Commit | Tests |
|--------|--------|-------|
| Securite labels + wording | `fc6de2d` | 16 |
| Socle trajectoire | `7b604bd` | 16 |
| Audit-trail + qualification source | `ff9a7b4` | 14 |
| Chaine de preuve export | `4ca8650` | 8 |
| Normalisation climatique | `a235ea3` | 8 |
| **Total** | **5 commits** | **62 tests** |

---

## Limites restantes

| Limite | Impact |
|--------|--------|
| DJU saisis manuellement (pas d'API Meteo France) | Donnees meteo non automatisees |
| Pas de normalisation de la baseline | Baseline supposee representative |
| Actor toujours "system" | Pas de tracking utilisateur reel |
| Pas de depot reel OPERAT | Simulation par design |
