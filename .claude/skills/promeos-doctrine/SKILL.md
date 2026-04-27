---
name: PROMEOS Doctrine
description: Doctrine produit/UX/data/engineering PROMEOS Sol v1.1. Activer pour toute tâche touchant cockpit, KPI, UX cœur, conformité, billing, achat, événements, scoring, ou tout écran user-facing. Ne PAS activer pour simples bugfixes ou refacto interne sans impact UX/data.
---

# PROMEOS Doctrine v1.1 — Activation

## Quand activer ce skill

✅ **Activer si la tâche touche** : création/modification d'écran cœur · ajout/calcul de KPI · règle conformité · scoring · copy user-facing · endpoint API public · refacto cockpit/portfolio/site · événement énergétique · standard d'erreur · contrat data.

❌ **Ne pas activer si** : bugfix backend pur · refacto code interne · maintenance dépendances · documentation technique uniquement · update de tests sans logique nouvelle.

## Comment l'utiliser

1. **Lire `references/principes.md`** (13 principes condensés) avant tout design.
2. **Lire `references/anti_patterns.md`** avant de proposer une solution.
3. **Lire `references/checklist_qa.md`** AVANT de marquer la tâche comme done.
4. Si KPI impliqué : `references/kpi_doctrine.md` + `backend/doctrine/kpi_registry.py`.
5. Si erreur API : `references/api_error_standard.md`.
6. Si événement : `references/event_card_schema.md`.
7. Pour la version intégrale : `references/doctrine_complete.md`.

## Auto-validation en fin de tâche

Avant de répondre "done", vérifier :

- [ ] Aucune règle métier dans le frontend
- [ ] Tout KPI affiché a unité + source + période visibles
- [ ] Constantes importées depuis `backend/doctrine/constants.py`
- [ ] États UX : loading, empty, error, partial data couverts
- [ ] Cohérence transverse vérifiée (si KPI déjà affiché ailleurs)
- [ ] Test source-guard ajouté si nouveau pattern critique
- [ ] PR template `Doctrine compliance` rempli
- [ ] Aucun acronyme brut en titre user-facing
- [ ] Org-scoping appliqué si endpoint nouveau
