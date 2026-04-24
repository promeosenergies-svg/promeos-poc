# Task 02 — Détecter secret committé pré-pilot

**Agent cible** : `security-auditor`
**Difficulté** : easy
**Sprint origin** : Secrets

## Prompt exact

> Scan le repo pour secrets (clés API, tokens, passwords) commitées. Focus PR en cours.

## Golden output (PASS)

- [ ] Scan pattern `AKIA[0-9A-Z]{16}` (AWS), `sk-[A-Za-z0-9]{48}` (OpenAI), etc.
- [ ] Focus pré-pilot (différence entre routine pré-commit owned par `code-reviewer`)
- [ ] Sévérité CVE Critical si match confirmé
- [ ] CWE-798 (hardcoded credentials)
- [ ] Délègue à `implementer` pour révocation + rotation

## Anti-patterns (FAIL)

- ❌ Doublonne avec `code-reviewer` (spécialités différentes)
- ❌ Laisse passer exemple clé "test"
- ❌ Pas de CWE

## Rationale

Dernier filet avant pilot. Secret = incident majeur en prod.
