# BACS Productization — Panel branche + Remediation actionnable

> Date : 2026-03-16
> Commit : `1200a26`
> Statut : Implemente, teste, pushe

---

## Ce qui est livre

### Integration UI
- `BacsRegulatoryPanel` branche dans **Site360 > Tab Conformite**
- Charge automatiquement les donnees via `getBacsRegulatoryAssessment(siteId)`
- Gere les etats loading / empty / error

### Remediation actionnable
Pour chaque blocker, le panel affiche :
- **Cause** : explication du probleme
- **Action** : correction attendue
- **Preuve** : document a fournir
- **Priorite** : badge couleur (critical rouge / high ambre / medium gris)

### 6 axes visibles dans le panel

```
BACS REGLEMENTAIRE                  [Statut]

⚠ Aide a la conformite

PERIMETRE
  Assujetti, Seuil, Putile, Echeance

EXIGENCES R.175-3 (X/10)
  ✓/✕ pour chaque exigence

EXPLOITATION / MAINTENANCE
  Consignes, Formation, Controles

INSPECTION
  Derniere, Prochaine, Overdue alert, Findings

PREUVES (N/4)
  ✕ types manquants

REMEDIATION (N actions)
  cause + action + preuve + priorite

BLOCKERS
  ⚠ liste blockers residuels
```

---

## Bilan conformite complet final (OPERAT + BACS)

| Zone | Commits | Tests |
|------|---------|-------|
| OPERAT | 8 | 96 |
| BACS compliance gate | 1 | 11 |
| BACS regulatory engine | 1 | 15 |
| BACS operations | 1 | 8 |
| **BACS productization** | **1** | **0 (UI)** |
| **Total** | **12** | **130** |

---

## Limites restantes

| Limite | Impact | Priorite |
|--------|--------|----------|
| CTA "Creer action corrective" pas encore connecte au systeme d'actions | Remediation en lecture seule | P2 |
| Upload fichier preuve non implemente | Reference texte uniquement | P2 |
| Notifications email echeances absentes | Alertes visibles uniquement dans l'app | P3 |
| Pas de workflow d'approbation inspection | Validation manuelle | P3 |
| Panel non encore dans ConformitePage (uniquement Site360) | Acces via fiche site | P3 |
