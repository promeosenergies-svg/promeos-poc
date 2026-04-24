# Task 02 — Range baseload tertiaire attendu

**Agent cible** : `ems-expert`
**Difficulté** : easy
**Sprint origin** : EMS / Baseload

## Prompt exact

> Un site tertiaire a baseload = 55% de la conso totale. Diagnostic ?

## Golden output (PASS)

- [ ] Range attendu tertiaire : **15-40%**
- [ ] 55% = ALERTE (trop haut) → dérive non pilotée
- [ ] Diagnostic : équipements toujours-on, CVC nuit, IT, veille
- [ ] Délègue à `data-connector` si CDC 30min manquante pour analyse
- [ ] Cite bench OID/CEREN par archétype NAF

## Anti-patterns (FAIL)

- ❌ Accepte 55% comme normal
- ❌ Pas de range cité
- ❌ Pas de cause identifiée

## Rationale

Test diagnostic basique avec seuils mémorisés.
