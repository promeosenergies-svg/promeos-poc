## 16. Governance engineering

Toute PR significative doit inclure une section doctrine.

```markdown
## Doctrine compliance

- Principes respectés : 1, 5, 10, 13
- Risques ou tensions : données partielles sur le site X
- KPI impactés : annual_consumption_mwh, energy_cost_eur
- Sources utilisées : Enedis, facture fournisseur, RegOps
- Tests ajoutés : unit KPI, integration API, e2e cockpit
- États UX couverts : loading, empty, error, partial data
```

### Critères de rejet d'une PR

Une PR doit être rejetée si :

- elle crée un KPI sans fiche ;
- elle calcule une règle métier dans le frontend ;
- elle affiche une valeur sans unité ;
- elle introduit une route morte ;
- elle ajoute une action non reliée à un objet métier ;
- elle casse la cohérence entre vues ;
- elle masque une donnée incertaine comme certaine.

---

## 17. Roadmap doctrine

### P0 — Socle MVP

- référentiel patrimoine propre ;
- KPIs unifiés ;
- cockpit briefing ;
- conformité principale ;
- consommation / performance ;
- qualité data visible ;
- centre d'action ;
- premiers contrôles facture.

### P1 — Crédibilité B2B

- shadow billing approfondi ;
- conformité avec preuves ;
- moteur d'événements ;
- connecteurs robustes ;
- exports experts ;
- logs et traçabilité ;
- scénarios achat simples.

### P2 — Best-in-world

- assistant éditorial énergétique ;
- adaptation par archetype ;
- intelligence achat post-ARENH ;
- flex score ;
- ACC starter ;
- systèmes locaux et personnalisés ;
- recommandations automatiques multi-modules.

---

