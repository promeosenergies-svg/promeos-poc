# Followup — Hygiène main local + incident IDE auto-switch (P2)

**Origine** : Audit Agents SDK — Phase 0 (2026-04-24) — détection pendant exécution étape 3
**Sévérité** : P2 — hygiène, pas bloquant
**Hors scope** : audit agents catalogue

## Incident 1 — Local main pollué par 2 commits nav

### Constat

Au moment de `git checkout main && git pull --ff-only origin main` :

```
Your branch is ahead of 'origin/main' by 2 commits.
(use "git push" to publish your local commits)
```

Commits concernés :
```
ec15f0bb docs(nav): success criteria Vague 1 + candidats Vague 2 deep-links
9b56e1a2 chore(nav): instrument vague-1 deep-links for usage analytics
```

### Provenance

- Présents aussi sur `claude/fix-site-compliance-score-header` (local)
- **Absents** d'origin/* — uniquement sur machine locale
- Non perdus (existent sur la branche locale ci-dessus)

### Mitigation appliquée

Audit agents SDK rebasé sur `origin/main` directement via :
```bash
git reset --hard origin/main  # sur claude/agents-sdk-catalogue
```

Résultat : la branche audit démarre propre depuis `a5e2424d` (tip origin/main).

### Action proposée pour main local

**Option A** (simple) : `git reset --hard origin/main` quand aucune session active n'a `main` comme base.
**Option B** (investigation) : déterminer la provenance (quelle branche devrait owner ces 2 commits ?). Sont-ils censés être sur `claude/nav-sol-parity-sprint-1-vague-b` ? Sur `claude/fix-site-compliance-score-header` qui les a déjà ?

Recommandation : **Option A** après confirmation que `claude/fix-site-compliance-score-header` est bien la branche owner (elle les contient déjà).

### Lien doctrine

Violation de la règle `feedback_no_main_pollution.md` ("Zero pollution main") :
- Perso / WIP ne doit jamais atterrir sur `main` local
- Si détecté, reset immédiat après vérification que les commits vivent ailleurs

## Incident 2 — IDE auto-switch branche pendant conversation

### Constat

Pendant la Phase 0, séquence reflog observée :

```
HEAD@{133} — checkout -b claude/agents-sdk-catalogue (commande intentionnelle)
HEAD@{132} — moved from claude/agents-sdk-catalogue to claude/nav-sol-parity-sprint-1-vague-b  ← NON INTENTIONNEL
HEAD@{131} — rebase (start) — rebase sur la mauvaise branche !
```

### Impact

- `git rebase origin/main` a rebasé **130 commits de SolPanel** au lieu de rebaser la branche audit
- `claude/nav-sol-parity-sprint-1-vague-b` localement désynchronisée (nouveaux SHAs)
- Remote intact (pas de push) → remediation = `git reset --hard origin/claude/nav-sol-parity-sprint-1-vague-b`

### Cause probable

Extension VSCode / Claude Code a auto-switch vers la branche "ouverte dans le workspace" pendant qu'une pause conversation (user valide option 1). Pattern non documenté.

### Mitigation appliquée

1. Reset `claude/nav-sol-parity-sprint-1-vague-b` sur origin (destructif mais isolé, reverse mistake)
2. `git checkout claude/agents-sdk-catalogue` + verification `git branch --show-current` après chaque switch
3. Usage du form explicite `git rebase <upstream> <branch>` qui check out explicitement la branche cible

### Action proposée

- **Documenter** le comportement dans memory (`feedback_ide_auto_switch_awareness.md`) — à créer
- **Ajouter** une règle : toujours `git branch --show-current` juste avant un `rebase/reset/merge` destructif
- **Enquêter** : est-ce une hook, une preference VSCode, ou un comportement par défaut de l'extension Claude Code ?

### Doctrine impactée

Renforce `feedback_parallel_sessions_awareness.md` + `feedback_git_discipline_refactor.md` :
- **Avant toute commande destructive** : verify current branch
- **Jamais chainer** rebase + checkout dans même `&&` sans verify intermédiaire

## Owner

Amine (investigation IDE) + followup memory update après enquête.

## Estimation

- Incident 1 : 2 min (reset quand safe)
- Incident 2 : 1-2h (enquête IDE + doc)
