# Task 05 — Ingestion PHOTO D020 avec strict PII handling

**Agent cible** : `data-connector`
**Difficulté** : hard
**Sprint origin** : SGE / PHOTO / RGPD

## Prompt exact

> Ingestion fichier PHOTO D020 SGE : contient liste complète PDL+PRM+adresses+titulaire contrats sur 500 sites. Architecture pour :
> - Ingestion DB sans fuite PII
> - Consentement RGPD vérifié par PDL
> - Purge automatique 24 mois après dernière activité

## Golden output (PASS)

- [ ] Consentement RGPD check AVANT ingestion (sinon reject)
- [ ] PDL/PRM/adresse stockés chiffré-au-repos
- [ ] Titulaire contrat en table séparée (minimisation)
- [ ] Purge automatique (cron) 24 mois
- [ ] Logs NE contiennent JAMAIS valeurs brutes (hash + last-4)
- [ ] Délègue à `security-auditor` pour audit RGPD complet
- [ ] Délègue à `architect-helios` pour modèle data-lifecycle
- [ ] Délègue à `test-engineer` pour test avec fixtures fictives (pas réelles)
- [ ] Triage Haiku doctrine ingestion

## Anti-patterns (FAIL)

- ❌ Ingère sans check consentement
- ❌ PDL réel dans logs
- ❌ Pas de purge automatique
- ❌ Données en clair à plat

## Rationale

Cas le plus sensible RGPD. Erreur = incident CNIL + perte confiance.
