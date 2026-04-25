# Task 03 — Parser flux R6X Enedis

**Agent cible** : `data-connector`
**Difficulté** : medium
**Sprint origin** : Ingestion / R6X

## Prompt exact

> Implémente parser R6X (flux Enedis index journaliers). Fichier CSV avec colonnes PRM, date, cadran, index. Ingestion DB + déduplication + checksum.

## Golden output (PASS)

- [ ] Parser CSV streaming (pas full-load mémoire)
- [ ] Déduplication (PRM, date, cadran) unique
- [ ] Checksum fichier vérifié
- [ ] PRM masqué dans logs (RGPD HELIOS)
- [ ] Triage Haiku si faits chiffrés (doctrine `feedback_ingest_triage.md`)
- [ ] Délègue à `test-engineer` pour test parse avec fichier fictif

## Anti-patterns (FAIL)

- ❌ PRM réel dans logs
- ❌ Load-all CSV en mémoire
- ❌ Pas de déduplication

## Rationale

Cas usage fréquent ingestion. Combine techno + RGPD + test.
