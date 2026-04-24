# Task 02 — Accise élec T1 février 2026

**Agent cible** : `bill-intelligence`
**Difficulté** : easy
**Sprint origin** : Bill / Accises

## Prompt exact

> Quel est le tarif accise élec T1 applicable à partir du 01/02/2026 ? Et pour T2 ?

## Golden output (PASS)

- [ ] Consulte YAML section `accise_elec_2026_t1` et `_t2`
- [ ] Cite valid_from 01/02/2026
- [ ] Source : Loi de finances 2026
- [ ] Distingue T1 et T2 (profils différents)
- [ ] Format tableau

## Anti-patterns (FAIL)

- ❌ Confondre TICGN (gaz deprecated) avec accise élec
- ❌ Reprendre ancienne valeur Aug 2025 sans césure
- ❌ Omettre profil (T1/T2)

## Rationale

Teste la gestion temporelle des césures tarifaires (V120 fix queue 1).
