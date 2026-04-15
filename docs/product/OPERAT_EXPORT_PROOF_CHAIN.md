# OPERAT Export — Chaine de preuve fermee

> Date : 2026-03-16
> Commit : `4ca8650`
> Statut : Implemente, teste, pushe

---

## Ce qui est livre

Chaque export OPERAT preparatoire genere desormais :
1. Un **manifest immuable** avec toutes les metadonnees
2. Un **checksum SHA-256** du contenu CSV
3. Un **event log** `export_generate` dans ComplianceEventLog
4. Des **headers HTTP** avec manifest ID + checksum
5. Des **warnings** si les sources sont faibles

---

## Nouveau modele : OperatExportManifest

```
id, efa_id, org_id, generated_at, actor, file_name,
checksum_sha256, observation_year, baseline_year, baseline_kwh,
current_kwh, baseline_source, current_source, baseline_reliability,
current_reliability, trajectory_status, efa_count,
evidence_warnings_json, export_version
```

---

## Chaine de preuve complete

```
Export OPERAT declenche
    │
    ├── 1. CSV genere (contenu)
    ├── 2. SHA-256 calcule sur le contenu
    ├── 3. Manifest cree avec :
    │       ├── checksum
    │       ├── baseline (year, kwh, source, reliability)
    │       ├── current (kwh, source, reliability)
    │       ├── trajectory_status
    │       ├── evidence_warnings
    │       └── actor + timestamp
    ├── 4. Event log export_generate
    └── 5. Headers HTTP :
            ├── X-PROMEOS-Manifest-Id
            ├── X-PROMEOS-Checksum-SHA256
            ├── X-PROMEOS-Submission-Type: simulation_preparatoire
            └── X-PROMEOS-Disclaimer
```

---

## Endpoints

| Methode | Path | Role |
|---------|------|------|
| GET | `/api/operat/export-manifests?org_id=N` | Historique 50 derniers exports |
| GET | `/api/operat/export-manifests/{id}` | Detail d'un manifest |

---

## Bloc UI : Historique exports preparatoires

```
┌──────────────────────────────────────────────────────┐
│ HISTORIQUE EXPORTS PREPARATOIRES                     │
│                                                      │
│ 16/03/2026  [Non atteinte] [Fiable]                  │
│ 3 EFA · 2025 · system                                │
│                          4ca8650a1b2c... 1 warning(s) │
│                                                      │
│ 15/03/2026  [Non evaluable] [Non verifiee]           │
│ 3 EFA · 2024 · api_user                              │
│                          8f2e1d3c4b5a... 2 warning(s) │
└──────────────────────────────────────────────────────┘
```

---

## Tests (8 passes)

| Test | Verifie |
|------|---------|
| manifest_created_with_checksum | Checksum SHA-256 present et 64 chars |
| manifest_actor_never_empty | Actor fallback "system" si null |
| manifest_captures_baseline | Baseline year/kwh/source/reliability stockes |
| manifest_warnings_if_no_baseline | Warning "reference absente" |
| manifest_warnings_if_low_reliability | Warning fiabilite faible |
| export_generates_event_log | Event log export_generate cree |
| different_content_different_checksum | Contenu different = checksum different |
| list_returns_manifests | Historique par org_id |

---

## Bilan conformite OPERAT complet

| Brique | Commit | Statut |
|--------|--------|--------|
| Securite labels + wording | `fc6de2d` | Livre |
| Socle trajectoire (baseline + -40/-50/-60) | `7b604bd` | Livre |
| Audit-trail + qualification source | `ff9a7b4` | Livre |
| Chaine de preuve export | `4ca8650` | Livre |

**Total : 4 commits conformite, 42+ tests backend, 12 tests front securite.**

---

## Limites restantes

| Limite | Impact |
|--------|--------|
| Normalisation climatique | Comparaisons biaisees par meteo |
| Actor toujours "system" | Pas de tracking utilisateur reel (IAM non branche) |
| Pas de signature numerique | Checksum sans certificat |
| Pas de depot reel OPERAT | Simulation uniquement (par design) |
| Pas de politique retention/archivage | Pas de suppression automatique |
