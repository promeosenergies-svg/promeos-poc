# Task 01 — Méthode DJU COSTIC base 18°C

**Agent cible** : `ems-expert`
**Difficulté** : easy
**Sprint origin** : EMS / DJU

## Prompt exact

> Quelle méthode DJU utilise PROMEOS pour la correction climatique d'un site tertiaire ?

## Golden output (PASS)

- [ ] Méthode **COSTIC base 18°C** (pas HDD Eurostat)
- [ ] Source : COSTIC / référentiel pro
- [ ] Distingue DJU chauffage (Tbase < Text) vs DJU clim
- [ ] Skill `@promeos-energy-fundamentals/SKILL.md` référencée

## Anti-patterns (FAIL)

- ❌ HDD Eurostat base 15°C
- ❌ Degree-days US "cooling/heating" formule mixte
- ❌ Valeur hardcodée base

## Rationale

Connaissance métier EMS basique. Erreur ici = correction climatique fausse.
