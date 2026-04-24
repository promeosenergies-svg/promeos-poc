# Task 04 — Checklist release pré-pilot push

**Agent cible** : `qa-guardian`
**Difficulté** : medium
**Sprint origin** : Release

## Prompt exact

> Avant pilot push HELIOS, valide : baseline tests PASS, source-guards PASS, source-guards CI PASS, security-auditor report Critical=0, code-reviewer PR approved.

## Golden output (PASS)

- [ ] Checklist 5 items traitée explicitement
- [ ] Délégations : `test-engineer` si baseline red, `security-auditor` si non-report, `code-reviewer` si PR non approvée
- [ ] Verdict `GO` ou `NO-GO` binaire
- [ ] Délai estimé si NO-GO (combien d'actions manquantes)

## Anti-patterns (FAIL)

- ❌ Verdict flou "probably OK"
- ❌ Oublie un item de la checklist
- ❌ Verdict GO avec Critical > 0

## Rationale

Checklist release blocking. Toute faille = incident prod.
