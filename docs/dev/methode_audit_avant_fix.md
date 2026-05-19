# Méthode — Audit avant fix (Phase 0/1 read-only)

> **Statut** : règle permanente. Sibling de `methode_walkthrough_navigateur.md`.
> Codifie le « Phase 0 read-only → STOP gate » du workflow CLAUDE.md.
> Livré M2-5.9 (solde l'item backlog M3-METHOD-DOC).

## Principe

Aucun code écrit avant un **audit read-only de l'existant**. Tout sprint
commence par une Phase 0/1 (grep / glob / read, **zéro modification**) qui
établit les **faits** du backend et du codebase réels, AVANT de suivre le plan
d'un prompt.

Le prompt énonce une **intention** ; le code réel énonce la **vérité**. En cas
de divergence, le code réel gagne — et si la divergence invalide une prémisse
cardinale du plan, **STOP** et retour en arbitrage avant de coder.

## Procédure

1. **Phase 0/1 read-only** — localiser et LIRE les fichiers que le sprint va
   toucher : modèles, schémas, signatures de fonctions, enums, helpers, tests
   déjà existants. Outils : `Grep`, `Glob`, `Read`. Aucune écriture.
2. **Confronter prompt ↔ réalité** — noter chaque divergence : nom de classe,
   signature, valeur d'enum, helper déjà présent, test qui couvre déjà le cas,
   prémisse fausse.
3. **STOP gate** — si une divergence invalide une prémisse cardinale du plan :
   revenir en chat, ne pas coder. Sinon : adapter, et documenter l'adaptation
   au bilan.
4. Puis seulement — phases d'implémentation numérotées → DoD → commit atomique
   → source-guard.

## Pourquoi — ce que l'audit a déjà rattrapé

- **M2-5.9** — le prompt voulait créer un SoT `link_vocab.py`. L'audit a montré
  que `models/v4/enums/target_module.py::TargetModule` est **déjà** le SoT
  (importé par le schéma et le validator) → le créer aurait **dupliqué** le
  SoT. Et que le `501` sur `regulatory_obligation` est correct → le « corriger »
  aurait été une régression de rigueur. ~1 j/h de travail nuisible évité.
- **M2-5.8.A** — le prompt supposait un modèle `User` plat. L'audit a révélé un
  modèle IAM relationnel (`User` + `UserOrgRole`), un `DEMO_MODE` constante
  figée à l'import, un `create_access_token` à signature positionnelle. Coder
  sur les hypothèses du prompt = ~200 lignes fausses.
- **M2-5.0 → .7** — à chaque sprint, les noms backend réels diffèrent des
  hypothèses du prompt (`ActionCenterItem` ≠ `ActionItem`, `Evidence` ≠
  `ActionEvidence`, champs `item_id` ≠ `action_item_id`…).
- **BACS / décrets** — vérifier la source officielle avant de citer un texte
  réglementaire : variante « audit avant affirmation »
  (cf. `feedback_verifier_derniers_decrets_sources` en mémoire projet).

## Anti-patterns

- ❌ Suivre le plan du prompt sans lire le code réel (« le prompt dit X »).
- ❌ Coder, puis découvrir la divergence au runtime ou au test.
- ❌ Deviner une signature / un nom de classe plutôt que le lire.
- ❌ « Petit sprint, audit overkill » — c'est précisément là que les
  hypothèses fausses passent.

## Quand l'audit est cardinal

Tout sprint. En particulier : sprints write backend (signatures, enums),
sprints sécu (helpers, scoping), refactos cross-modules, et tout sprint dont
le prompt a été rédigé sans accès au code.

## ROI

| Sprint | Audit | Évité |
|--------|-------|-------|
| M2-5.9 | ~15 min | ~1 j/h de travail nuisible + 1 régression de rigueur |
| M2-5.8.A | ~15 min | ~200 lignes codées sur des hypothèses fausses |

Coût / bénéfice systématiquement > 1:10.
