# Followup — WIP `audit/v1/` non-documenté (P2)

**Origine** : Phase 4 pre-check (2026-04-24)
**Sévérité** : P2 — WIP externe à l'audit agents SDK
**Hors scope** : audit agents (session parallèle utilisateur)

## Constat

Dossier `audit/v1/` au repo root, untracked, contenant 4 fichiers de cartographie :

```
audit/v1/
├── v1_cartographie_backend.md      (15 KB, créé 2026-04-24 09:04)
├── v1_cartographie_main_front.md   (14 KB, créé 2026-04-24 09:00)
├── v1_cartographie_refonte_sol_front.md (12 KB, créé 2026-04-24 09:02)
└── v1_diff_strategique.md          (13 KB, créé 2026-04-24 09:05)
```

## Analyse

- **Provenance** : session/agent parallèle — les fichiers référencent explicitement `worktree: /Users/amine/projects/promeos-audit-main/` et `promeos-audit-refonte-sol/` comme origines
- **Timeline** : créés pendant l'exécution de la Phase 3A (09:00-09:05), donc **pas par cette session Claude Code**
- **Contenu** : cartographie legitimate audit frontend (routes React, App.jsx) comparant `origin/main` (a5e2424d) vs `origin/claude/refonte-visuelle-sol` (261e3a2e, +119 commits)
- **Hors scope audit agents SDK** : ne concerne pas les 11 AgentDefinitions

## Décision

- **Ne pas committer** sur `claude/agents-sdk-catalogue` (hors scope PR #260)
- **Ne pas supprimer** (WIP utilisateur potentiellement important)
- **Laisser untracked** jusqu'à arbitrage user

## Action proposée pour l'utilisateur

1. Vérifier quelle session/worktree produit ces fichiers (`/Users/amine/projects/promeos-audit-main/` ?)
2. Si WIP valide → commit sur branche dédiée `claude/audit-refonte-sol-cartographie` ou similaire
3. Si obsolète → `rm -rf audit/v1/`
4. Considérer ajouter `audit/` à `.gitignore` si dossier temporaire par convention

## Root cause potentielle

Sessions Claude Code parallèles + worktrees multiples (cf. incident IDE auto-switch Phase 0 — `local_main_hygiene.md`). Pattern à surveiller : si les worktrees écrivent au repo root sans discipline branche claire, les artefacts polluent les autres branches.

## Owner

Amine (identification de la session productrice + décision commit/delete).

## Estimation

5 min (identification) + action suivant décision.
