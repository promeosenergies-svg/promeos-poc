# OPERAT Hardening Final — Cloture avant pivot BACS

> Date : 2026-03-16
> Commit : `cb26d61`
> Statut : Implemente, teste, pushe

---

## Points renforces

| Zone | Avant | Apres |
|------|-------|-------|
| **Archivage** | Aucune retention | retention_until = 5 ans, archive_status active/archived/expired |
| **Certification** | checksum seul | + promeos_version 2.0 + weather_provider + baseline_norm_status |
| **Actor** | Souvent "system" | resolve_actor() propage dans export + declare |
| **Meteo** | Source non qualifiee dans manifest | weather_provider stocke + source_ref expose |

---

## Bilan conformite OPERAT complet (8 commits, 84 tests)

| # | Brique | Commit | Tests |
|---|--------|--------|-------|
| 1 | Securite labels + wording | `fc6de2d` | 16 |
| 2 | Socle trajectoire (-40/-50/-60) | `7b604bd` | 16 |
| 3 | Audit-trail + qualification source | `ff9a7b4` | 14 |
| 4 | Chaine de preuve export (manifest/checksum) | `4ca8650` | 8 |
| 5 | Normalisation climatique DJU | `a235ea3` | 8 |
| 6 | Gouvernance statut final | `85cf130` | 9 |
| 7 | Source trust (meteo + actor + baseline) | `225d612` | 15 |
| 8 | **Hardening final** | **`cb26d61`** | **10** |
| | **Total** | **8 commits** | **84+12=96 tests** |

---

## Ce qui est defendable maintenant

| Capacite | Preuve |
|----------|--------|
| Trajectoire -40/-50/-60 calculee | Service + 16 tests |
| Consommation reference verrouillable | Unicite + validation |
| Source qualifiee (high/medium/low/unverified) | 14 tests |
| Fallback JAMAIS classe high | Test automatise |
| Export reconstituable | Manifest SHA-256 + metadata |
| Audit-trail immuable | ComplianceEventLog |
| Normalisation DJU transparente | Brute + normalisee coexistent |
| Statut final gouverne | 4 modes (raw/normalized/mixed/review) |
| Source meteo tracee | Provider + source_ref + confidence |
| Actor identifie | Email > user_id > header > fallback |
| Archivage 5 ans | retention_until sur manifest |
| Version tracee | promeos_version dans manifest |

---

## Limites acceptees pour le pivot BACS

| Limite | Statut |
|--------|--------|
| DJU estimes (pas API Meteo-France externe) | Accepte — table RT2012 = source verifiee interne |
| Pas de signature numerique X.509 | Accepte — checksum SHA-256 present |
| Pas de depot reel OPERAT | Par design — simulation preparatoire |
| Actor partiellement "system" quand auth absente | Accepte — fallback explicite |
| Pas de purge automatique apres retention | Futur — statut archive expose |

---

## Pret pour pivot BACS
