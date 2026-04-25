# Task 04 — CTA additive gaz (formule V114)

**Agent cible** : `bill-intelligence`
**Difficulté** : medium
**Sprint origin** : Bill / CTA

## Prompt exact

> Explique et applique la formule CTA gaz "additive" livrée V114. Exemple : facture ATRD T3 gaz, 200 MWh sur un mois, puissance souscrite 500 kW. Calcule CTA.

## Golden output (PASS)

- [ ] Formule correcte : CTA = coef × base puissance (pas proportionnel conso)
- [ ] Cite memory `project_billing_vague2_backlog.md`
- [ ] Distingue CTA ancien (2021) vs CTA post fév 2026
- [ ] Source : ATRD gaz + décret CTA
- [ ] Format JSON anomalies si divergence

## Anti-patterns (FAIL)

- ❌ CTA proportionnelle conso (formule erronée)
- ❌ Oublier puissance souscrite
- ❌ Pas de citation source

## Rationale

Formule subtile, livrée récemment. Teste la connaissance V112-V114.
