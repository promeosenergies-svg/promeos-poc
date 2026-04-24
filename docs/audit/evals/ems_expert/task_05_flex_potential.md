# Task 05 — Flex potential par usage (NEBCO éligibilité)

**Agent cible** : `ems-expert`
**Difficulté** : hard
**Sprint origin** : Flex / NEBCO

## Prompt exact

> Un site archétype "Bureau" (NAF 6820A), puissance pilotable CVC 40 kW, conso HP 800 MWh/an. Calcule flex potential pour éligibilité NEBCO + estimation gain €/kW·an.

## Golden output (PASS)

- [ ] Décompose flex par usage (CVC, froid, IRVE, batterie)
- [ ] Applique archétype NAF (6820A = tertiaire bureau)
- [ ] Éligibilité NEBCO : seuil minimal puissance pilotable + historique
- [ ] Gain estimé 80-100 €/kW·an (range NEBCO 2026, memory `project_flexibilite_strategie_produit`)
- [ ] Délègue à `regulatory-expert` pour vérif règles NEBCO actuelles
- [ ] Délègue à `bill-intelligence` pour impact facture
- [ ] Format JSON + unités
- [ ] Skill `@energy-flexibility-dr/SKILL.md` chargée

## Anti-patterns (FAIL)

- ❌ Calcul flex sans archétype NAF
- ❌ Oublier la règle NEBCO actuelle (seuils évolutifs)
- ❌ Gain inventé sans citation

## Rationale

Feature différenciante PROMEOS. Cross-domaine : NAF + CDC + réglementaire + économie.
