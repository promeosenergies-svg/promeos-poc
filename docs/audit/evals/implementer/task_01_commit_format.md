# Task 01 — Format commit canonical

**Agent cible** : `implementer`
**Difficulté** : easy
**Sprint origin** : Discipline / Git

## Prompt exact

> J'ai implémenté un fix de typo dans `backend/routes/sites.py`. Propose un commit message.

## Golden output (PASS)

- [ ] Format `type(module-pN): Phase X.Y — description`
- [ ] Type `fix` cohérent (ou `chore(typo)`)
- [ ] Description courte (<72 chars ligne 1)
- [ ] Référence de module claire

## Anti-patterns (FAIL)

- ❌ "Fixed typo" (trop court, pas de format)
- ❌ Message > 72 chars ligne 1 sans justification
- ❌ Ajoute `Co-Authored-By` non demandé

## Rationale

Discipline de base. Doctrine feedback_commit_push_immediately.
