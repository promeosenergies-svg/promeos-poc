# Task 05 — Prompt différenciation vs concurrent

**Agent cible** : `prompt-architect`
**Difficulté** : hard
**Sprint origin** : Prompts / Stratégie

## Prompt exact

> Un PM veut copier une feature de Advizeo (ex-Hager) pour PROMEOS. Génère un prompt qui oblige le bench + évaluation différenciation AVANT d'écrire la feature, pour éviter me-too.

## Golden output (PASS)

- [ ] Phase 0 **Competitive bench** (Advizeo + Metron + Deepki + Hello Watt) read-only
- [ ] STOP gate : valider différenciation PROMEOS (neutralité, usage fil conducteur, flex NEBCO)
- [ ] Si feature me-too → `NO-GO` explicite avec rationale
- [ ] Si différenciation claire → phase 1+ avec délégation par agent
- [ ] Références memory `project_competitive_hellowatt`, `project_mix_e_2026_competitive_analysis`
- [ ] Réponse structurée PM-friendly (pas trop technique)

## Anti-patterns (FAIL)

- ❌ Pas de phase bench
- ❌ Accepte me-too sans alerte
- ❌ Ignore positioning "Fournisseur 4.0 sans vendre un kWh"

## Rationale

Méta-competence stratégique. Évite dérive produit vers copies concurrents.
