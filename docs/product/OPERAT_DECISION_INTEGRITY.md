# OPERAT Decision Integrity — Gouvernance statut final

> Date : 2026-03-16
> Commit : `85cf130`
> Statut : Implemente, teste, pushe

---

## Probleme resolu

Le statut final basculait automatiquement vers "normalise" des qu'une normalisation existait, meme si :
- la source meteo etait manuelle non verifiee
- la confiance etait faible
- la baseline n'etait pas normalisee (base mixte)

---

## Regles d'arbitrage

| Condition | final_status | mode |
|-----------|-------------|------|
| Pas de normalisation | raw_status | `raw_only` |
| Normalisation + confiance high/medium + source verifiee + baseline normalisee | normalized_status | `normalized_authoritative` |
| Normalisation + confiance high/medium + source verifiee + baseline NON normalisee | normalized_status + warning | `mixed_basis_warning` |
| Normalisation + confiance low | `review_required` | `review_required` |
| Normalisation + source manuelle non verifiee | `review_required` | `review_required` |

**Principe : le statut ne bascule JAMAIS vers un optimisme non justifie.**

---

## Source meteo

| weather_data_source | weather_source_type | source_verified |
|--------------------|--------------------|----------------|
| meteo_france | api | true |
| api | api | true |
| file_import | file_import | true |
| manual | manual | **false** |
| unknown | unknown | **false** |

Source manuelle → `review_required` obligatoire, meme si confiance high.

---

## Major warnings

Affiches en **rouge** dans l'UI (au-dessus des warnings ambre) :

- "Statut base sur donnees brutes non normalisees" (raw_only)
- "Confiance normalisation faible — revue requise" (low confidence)
- "Source meteo non verifiee (saisie manuelle) — revue requise"
- "Baseline non normalisee — comparaison sur base mixte"

---

## UI enrichie

```
TRAJECTOIRE OPERAT  [Brut]  [Revue requise]
                ou  [Normalise]  [Trajectoire atteinte]
                ou  [Base mixte]  [Non atteinte]

Major warnings (rouge) :
  ⚠ Source meteo non verifiee — revue requise
  ⚠ Baseline non normalisee — comparaison sur base mixte

Warnings (ambre) :
  Donnees non normalisees climatiquement
```

---

## Audit-trail

- Event log `normalize` cree a chaque normalisation (avec DJU, methode, source)
- Actor jamais vide

---

## Tests (9 passes)

| Test | Verifie |
|------|---------|
| raw_only_when_no_normalization | Mode raw_only correct |
| normalized_authoritative_when_verified_high | Mode autorise quand fiable |
| review_required_when_low_confidence | Prudence si confiance faible |
| review_required_when_manual_source | Prudence si source manuelle |
| mixed_basis_when_baseline_not_normalized | Warning base mixte |
| major_warnings_in_raw_only | Warning brut toujours present |
| normalize_creates_event | Audit-trail |
| meteo_france_is_verified | Source verifiee |
| manual_is_not_verified | Source non verifiee |

---

## Bilan conformite OPERAT complet

| Brique | Commit | Tests |
|--------|--------|-------|
| Securite labels + wording | `fc6de2d` | 16 |
| Socle trajectoire | `7b604bd` | 16 |
| Audit-trail + qualification source | `ff9a7b4` | 14 |
| Chaine de preuve export | `4ca8650` | 8 |
| Normalisation climatique DJU | `a235ea3` | 8 |
| **Gouvernance statut final** | **`85cf130`** | **9** |
| **Total** | **6 commits** | **71 tests** |

---

## Limites restantes

| Limite | Impact |
|--------|--------|
| DJU saisis manuellement (pas d'API Meteo France) | Source non verifiee par defaut |
| Actor toujours "system" | Pas de tracking utilisateur reel |
| Pas de normalisation baseline | Baseline supposee representative |
| Pas de depot reel OPERAT | Simulation par design |
| Pas de signature numerique exports | Checksum sans certificat |
