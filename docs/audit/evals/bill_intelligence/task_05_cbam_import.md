# Task 05 — Intégration CBAM facture import acier

**Agent cible** : `bill-intelligence`
**Difficulté** : hard
**Sprint origin** : CBAM / P3 priorité

## Prompt exact

> Client industriel importe 500 tonnes acier Turquie/Inde. Comment intégrer l'impact CBAM dans le shadow billing énergie ? Scope, prix carbone, déclaration.

## Golden output (PASS)

- [ ] Clarifie périmètre CBAM (6 scopes : ciment, acier, alu, engrais, élec, H₂)
- [ ] Prix carbone EU ETS référent (~75 €/tCO₂ actuel)
- [ ] Déclarant = importateur UE
- [ ] Fin phase transition 2034
- [ ] Délègue à `regulatory-expert` pour scope exact + évolutions
- [ ] Délègue à `architect-helios` si brique CBAM à modéliser
- [ ] Format JSON `{finding, scope_cbam, prix_carbone, declaration, deadline}`

## Anti-patterns (FAIL)

- ❌ CBAM = taxe énergie interne (mauvais concept)
- ❌ Oublie que CBAM = importations hors UE
- ❌ Pas de délégation cross-agent

## Rationale

Sujet P3 stratégique (memory project_strategic_priorities). Cas first-mover B2B France.
