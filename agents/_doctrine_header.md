## Contrat doctrinal PROMEOS Sol v1.1

Tu interviens sur PROMEOS Sol — cockpit énergétique B2B post-ARENH.

**Règles inviolables** :

- Tout est lié (patrimoine → données → KPIs → actions → conformité → billing → achat).
- Non-sachants d'abord, sachants respectés.
- Zéro KPI magique : tout KPI a fiche YAML (`backend/doctrine/kpi_registry.py`).
- Constantes inviolables depuis `backend/doctrine/constants.py` uniquement (CO₂ élec 0.052, gaz 0.227, primary energy 1.9, fallback prix 0.068, DT jalons -40/-50/-60, NEBCO 100kW, accise élec T1 30.85 / T2 26.58, accise gaz 10.73).
- Statuts data : réel | estimé | incomplet | incohérent | en attente | démo. Pas de fallback silencieux.
- Zéro logique métier dans le frontend.
- Erreurs API standard : `{code, message, hint, correlation_id, scope}`.
- Org-scoping obligatoire (`resolve_org_id`).
- Chaque chiffre a son unité, sa source, sa période.

**Anti-patterns rejetés** : tableau sans synthèse, KPI sans source, graphique sans période, bouton sans destination, mock non signalé, règle non versionnée, valeur estimée affichée comme certaine.

**Definition of Done** : §15 (checklist QA) + §18 (cohérence transverse, sources visibles, traçabilité).

**Référence complète** : `docs/doctrine/doctrine_promeos_sol_v1_1.md`.
