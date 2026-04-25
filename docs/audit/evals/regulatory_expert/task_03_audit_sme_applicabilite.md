# Task 03 — Applicabilité Audit SMÉ

**Agent cible** : `regulatory-expert`
**Difficulté** : medium
**Sprint origin** : RegOps / Audit

## Prompt exact

> Organisation avec 5 M€ CA, 300 salariés, conso totale 3 GWh. Audit énergétique obligatoire ? ISO 50001 ? Quelles deadlines ?

## Golden output (PASS)

- [ ] Audit énergétique : OUI (> 2,75 GWh), deadline **11/10/2026**
- [ ] ISO 50001 : NON (≤ 23,6 GWh), mais veille si conso croît
- [ ] Source : Loi n°2025-391
- [ ] Sanctions : 1 500 €/an non-réalisation audit
- [ ] Format JSON `{finding, source, date_of_truth, applicability}`

## Anti-patterns (FAIL)

- ❌ Confondre CA et conso
- ❌ Citer ancien seuil 500 salariés
- ❌ Ignorer sanctions

## Rationale

Test applicabilité multi-critères (conso + structure). Cas scoring réel.
