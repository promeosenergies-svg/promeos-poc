# Sprint 3 Step 2 — Refresh cible au lieu de window.location.reload

> Date : 2026-03-15
> Commit : `258cf06`
> Statut : Implemente, teste, committe

---

## Probleme

3 occurrences de `window.location.reload()` dans Patrimoine.jsx provoquaient un rechargement complet de la page (flash blanc) apres :
- creation rapide de site (QuickCreateSite)
- creation avancee (SiteCreationWizard)
- edition depuis le drawer (DrawerEditSite/onSiteUpdated)

---

## Strategie de refresh

`refreshSites()` seul ne suffisait pas — il recharge les sites mais PAS les KPIs ni les contrats.

### Mecanisme mis en place

```
handleDataMutation()
    ├── refreshSites()       → recharge scopedSites (tableau + heatmap + stats)
    └── dataVersion bump     → recharge KPIs registre + contrats
```

| Donnees | Source | Mecanisme | Resultat |
|---------|--------|-----------|----------|
| Tableau sites | scopedSites (ScopeContext) | refreshSites() | Recharge |
| Stats (conformes, risque) | useMemo(scopedSites) | Auto-recalcul | Recharge |
| Heatmap | useEffect(scopedSites) | Re-execute | Recharge |
| KPIs registre | useEffect([org, siteId, dataVersion]) | dataVersion bump | Recharge |
| Contrats | useEffect([org, siteId, dataVersion]) | dataVersion bump | Recharge |
| Drawer completude | getSiteCompleteness(refreshKey) | refreshKey prop | Deja en place |

---

## Modifications

| Fichier | Ligne(s) | Modification |
|---------|----------|-------------|
| `Patrimoine.jsx` | 154 | Ajouter `refreshSites` au destructuring `useScope()` |
| `Patrimoine.jsx` | 156-160 | Ajouter `dataVersion` state + `handleDataMutation` callback |
| `Patrimoine.jsx` | 247 | Ajouter `dataVersion` aux deps useEffect KPIs |
| `Patrimoine.jsx` | 258 | Ajouter `dataVersion` aux deps useEffect contrats |
| `Patrimoine.jsx` | 1585, 1595, 1602 | `window.location.reload()` → `handleDataMutation()` |

Zero changement backend.

---

## Tests

| Test | Resultat |
|------|----------|
| 31 tests backend | Passe |
| 63 tests frontend | Passe |
| Build Vite | Passe |

---

## Ce qui reste Sprint 3

| Step | Action | Effort |
|------|--------|--------|
| S3-3 | Import simplifie (retirer Assiste + Demo du wizard) | M |
| S3-4 | Validation finale Sprint 3 | S |
