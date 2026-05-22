# Méthode — Self-review PR avant merge

> **Statut** : règle permanente. Sibling de `methode_audit_avant_fix.md` et
> `methode_walkthrough_navigateur.md`. Codifie la pause à froid validée
> empiriquement 4 fois pendant la phase M2. Livrée M2-6.0.

## Origine — quatre paiements en une phase

Quatre self-reviews intermédiaires de M2-5 ont livré des finds que ni les tests
verts ni les audits 6 agents synchrones (code-reviewer, qa-guardian,
security-auditor, 3× explore) n'avaient détectés :

1. **M2-5.9.bis** — 6 finds dont **CWE-307** rate-limit absent sur
   `/auth/demo-login` (sécu cardinal pilote payant).
2. **M2-5.10.A.bis** — 4 P0 fidélité Sol + 3 P1 code post-spec maquette.
3. **M2-5.10.B.bis** — V4Drawer custom (le legacy fuyait du focus trap),
   `ItemClosedBanner` manquant, label dynamique masthead faux.
4. **M2-5.10.bis clôture** — 4 Familles cross-pages, verdicts UX 6.5→8.5/10.

Total : **20 finds livrés sur 13 h investies**, dont 3 P0/sécu, bénéfice évité
~90 h de debugging post-pilote.

## Pourquoi les audits multi-agents ne suffisent pas

Les audits 6 agents sont **synchrones** avec le travail : ils inspectent ce qui
est devant eux à l'instant T. Ils ne voient pas :

- les **incohérences cross-pages** qui n'apparaissent qu'en navigation réelle ;
- les **détails UX** qui sautent aux yeux à froid (copy contradictoire,
  hiérarchie visuelle bancale, micro-bug pluriel `1 blocages`) ;
- les **régressions subtiles** accumulées depuis le début du sprint (item
  closed qui permet une écriture, filter qui ne reset pas `page=1`) ;
- les **fuites mineures CWE** dans le flot d'un sprint dense ;
- les **divergences entre maquette mentale et résultat livré**.

La self-review à froid voit ce que l'œil saturé ne voit plus.

## Règle permanente

Toute PR (ou phase trunk-based) qui livre **l'un** de :

- ≥ 3 commits cohérents formant une feature complète ;
- du code touchant l'UI sur plusieurs pages ;
- des changements sécurité, auth, ou middleware ;
- des modifications backend exposées en API publique

**DOIT inclure une self-review à froid AVANT merge / fin de phase**, ≥ 5 étapes :

1. **Pause minimum 24 h** depuis le dernier commit (cardinal — la fatigue
   contamine l'œil avant le code).
2. **Walkthrough navigateur complet** (cf. `methode_walkthrough_navigateur.md`).
3. **Relecture diff GitHub UI** des commits cumulés depuis le début de la phase.
4. **Test parcours pilote représentatif** bout en bout, en se mettant à la
   place de l'utilisateur cible.
5. **Action sur les finds** :
   - P0 fonctionnel/sécu → hotfix `.bis` avant merge ;
   - P1 UX → arbitrage (hotfix ou ticket M3+) ;
   - P2 polish → backlog M3+.

## Cas particulier — Trunk-based sans PR intermédiaire

Pattern adopté pour M2-6 (commits directs sur `claude/refonte-sol2`).

Sans PR review GitHub UI, la discipline self-review est **encore plus
critique** : aucune pause forcée par le merge n'existe.

Adaptation :

- À la fin de **chaque sous-sprint** (M2-6.A / M2-6.B / M2-6.C), pause 24 h
  avant le sous-sprint suivant.
- Walkthrough navigateur **obligatoire** entre sous-sprints (pas Phase 9
  seule du sprint qui clôt).
- Diff cumulé via `git log --oneline <fork-point>..HEAD`, relecture commit
  par commit dans l'UI GitHub (vue arbre, pas vue plat).
- En fin de phase complète : self-review finale + **4-eyes review** (peer
  externe si pilote payant, sinon self-review à froid à J+24 h).

## Anti-patterns

- ❌ « Les audits 6 agents sont verts, on merge » — faux dès que la phase
  cumule ≥ 3 commits ou touche UX/sécu.
- ❌ « J'ai déjà fait un `.bis` intermédiaire, pas besoin de self-review
  finale » — un `.bis` intermédiaire ne remplace pas la pause à froid sur la
  phase complète.
- ❌ « Le pilote n'est pas encore en cours, on hotfixera plus tard » — vrai
  pour P2 polish, faux pour P0 sécu et P1 UX cardinal.
- ❌ « Self-review = inflation, on perd 24 h » — faux, ROI mesuré ≥ 1:7
  (cf. table).

## ROI mesuré (M2-5)

| Self-review        | Finds | Sévérité max     | Coût (h) | Évité (h) |
|--------------------|-------|------------------|----------|-----------|
| M2-5.9.bis         | 6     | CWE-307 sécu     | 4        | ~40       |
| M2-5.10.A.bis      | 7     | P0 fidélité Sol  | 3        | ~15       |
| M2-5.10.B.bis      | 3     | P0 V4Drawer      | 2        | ~10       |
| M2-5.10.bis clôt.  | 4 fam.| P0 UX cross-pages| 4        | ~25       |
| **Total M2-5**     | **20**| **3× P0/sécu**   | **13**   | **~90**   |

Ratio moyen 1:7. Sur sécu seule (CWE-307 pilote payant), ratio ≥ 1:10.

## Lien avec les autres doctrines

Les 3 fichiers `methode_*.md` forment un système triphasé :

- **`methode_audit_avant_fix.md`** — *avant* le code : vérifier les prémisses
  du prompt contre le code réel (Phase 0 read-only).
- **`methode_walkthrough_navigateur.md`** — *pendant et après* chaque sprint :
  vérifier le comportement runtime (routing / auth / chaîne UI).
- **`methode_self_review_pr.md`** — *à la fin* d'une phase : vérifier la
  cohérence globale à froid (étapes 2 et 4 réutilisent le walkthrough).
