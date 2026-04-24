# Task 05 — Fix test flaky (race condition)

**Agent cible** : `test-engineer`
**Difficulté** : hard
**Sprint origin** : CI stability

## Prompt exact

> Test `test_billing_aggregation` passe en local mais fail 20% du temps en CI. Les timestamps de fixtures varient. Diagnostic + fix.

## Golden output (PASS)

- [ ] Identifie la cause : horloge + fixtures non-déterministes
- [ ] Propose `freezegun` ou `monkeypatch` sur `datetime.utcnow`
- [ ] Seed RNG=42 cohérent
- [ ] Test passe 100 fois de suite en CI simulation
- [ ] Délègue à `architect-helios` si pattern récurrent nécessite refacto fixture framework

## Anti-patterns (FAIL)

- ❌ `@pytest.mark.flaky(reruns=3)` (masquer, pas fixer)
- ❌ Ignorer
- ❌ Sleep pour synchroniser

## Rationale

Flaky = poison CI. Doctrine : fixer au root cause, jamais masquer.
