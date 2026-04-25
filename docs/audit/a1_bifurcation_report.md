# Vérification bifurcation A1 — Sprint 1 Vague A

> **Date audit** : 2026-04-23
> **Commits analysés** : `80d7121a15d24b89cc9d47ff1626addbbc10156b` + `75bc32c802983639146e8baa04c45205afa119a2`
> **HEAD au moment audit** : `249a4ef9` (branche `claude/refonte-visuelle-sol`)

## 0. Synthèse — verdict inattendu

L'hypothèse initiale du bilan Sprint 1 (« bifurcation + fast-forward merge ») était **erronée**.
Les deux commits sont **séquentiels linéaires**, pas concurrents. Le 2e est le descendant
direct du 1er. Il n'y a jamais eu de divergence git à aucun moment.

→ Verdict : **CAS A étendu (A')** — séquentiel cumulatif, pas bifurcation.
→ Action : `git push -u origin claude/refonte-visuelle-sol`, GO Vague B.

## 1. Métadonnées commits

| Champ              | `80d7121a`                                         | `75bc32c8`                                         |
|--------------------|----------------------------------------------------|----------------------------------------------------|
| Auteur             | Amine Ben Amara                                    | Amine Ben Amara                                    |
| Email              | amine@MacBook-Pro.local                            | amine@MacBook-Pro.local                            |
| Timestamp          | 2026-04-22 23:13:56 −0700                          | 2026-04-22 23:14:47 −0700                          |
| Δ temps            | —                                                  | **+51 secondes**                                   |
| Message (subject)  | `fix(aper-sol): restore useSearchParams filtering + active filter badge` | identique                                          |
| Parent             | `b0f47ad13b864a708204483c4a27ffd9d7ec5393` (audit fresh pre-Sprint) | **`80d7121a15d24b89cc9d47ff1626addbbc10156b`** (→ 80d7121a) |
| Fichiers modifiés  | 3 (AperSol.jsx + sol_presenters.js + AperSol.deep_link.test.js) | 1 (sol_presenters_filter.test.js, nouveau)        |
| Lignes +/−         | +258 / −2                                          | +68 / 0                                            |

> **Finding critique** : `75bc32c8.parent = 80d7121a` — c'est un commit enfant, pas concurrent.
> Même auteur, même session, +51s plus tard, avec un message subject identique mais un body
> différent. Aucun fork, aucune bifurcation git.

## 2. Diff strict entre les 2 commits

```text
 frontend/src/pages/aper/__tests__/sol_presenters_filter.test.js | 68 ++++++++++++++++++++++
 1 file changed, 68 insertions(+)
```

Le diff se résume à **un seul ajout** : `frontend/src/pages/aper/__tests__/sol_presenters_filter.test.js`
(68 L, 8 tests unitaires purs sur `normalizeAperFilter` + `applyAperFilter`).

Aucun fichier modifié dans le 1er commit n'est touché par le 2e — c'est un pur ajout
cumulatif.

### Verdict diff
- [x] Diff non-vide MAIS uniquement additif (nouveau fichier)
- [ ] Divergence partielle (modifications concurrentes)
- [ ] Divergence totale

## 3. Topologie git

### Ancêtre commun
```
git merge-base 80d7121a 75bc32c8
→ 80d7121a15d24b89cc9d47ff1626addbbc10156b (= 80d7121a lui-même)
```

L'ancêtre commun **est** le 1er commit. `75bc32c8` en descend directement.

### Graphe ASCII
```
* 249a4ef9 (HEAD -> claude/refonte-visuelle-sol) refactor(nav-sol): simplify
* 662cfe1d fix(polish): NBSP FR + icon distinct + tracker sanitize
* 97984b6c test(nav-sol): dynamic invariants
* 8e3d7ea8 fix(a11y): P1 keyboard nav
* a87286b6 fix(a11y): P0 locked items
* 26c12958 (claude/nav-sol-parity-sprint-1-vague-a) fix(test): SolPanel.locked regex
* 8b272890 feat(analytics): nav deep-links tracking
* 56d09b6a fix(a11y): focus rings SolPanel + SolRail
* 973f7ce0 feat(a11y): keyboard navigation
* 76fa3151 fix(a11y): skip link
* 956caf21 fix(nav): aper-legacy + invariant
* 9300f774 refactor(nav): remove 3 broken /conformite/*
* 7062b6a7 feat(nav): 6 admin items
* 175ecb9b feat(sol-panel): locked badge
* 1c2f11be feat(sol-panel): hasPermission + PERMISSION_KEY_MAP
* 75bc32c8 (origin/claude/refonte-visuelle-sol) fix(aper-sol): …
* 80d7121a fix(aper-sol): …
* b0f47ad1 docs(audit): fresh navigation Sol audit pre-Vagues ABCD
```

**Histoire 100% linéaire.** Pas de `|\`, pas de `*\/`, pas de merge commit. `origin/claude/refonte-visuelle-sol` est actuellement au tag `75bc32c8` (2e commit) — toute la suite est locale non-pushée.

### Commits entre les deux
- `git rev-list 80d7121a..75bc32c8` → `75bc32c8` seul (1 commit d'écart)
- `git rev-list 75bc32c8..80d7121a` → vide (aucun commit)

### Les 2 commits dans HEAD ?
- `80d7121a` : **IN HEAD** (ancêtre de `249a4ef9`)
- `75bc32c8` : **IN HEAD** (ancêtre de `249a4ef9`, même branche linéaire)

Aucun commit en orphelin. Aucun commit à recoller. Aucune trace de fork.

## 4. État runtime AperSol (cohérence intention A1)

- [x] `useSearchParams` présent : `frontend/src/pages/AperSol.jsx:13` (import) + L84 (consommation)
- [x] Filtres `?filter=parking|toiture` : `normalizeAperFilter(searchParams.get('filter'))` L88 + `applyAperFilter(data.dashboard, activeFilter)` L110
- [x] Badge filtre actif : `{activeFilter && (...)}` L157, "Filtre actif" + `FILTER_LABELS[activeFilter]` L194-196
- [x] Tests AperSol présents :
  - `frontend/src/pages/__tests__/AperSol.deep_link.test.js` — **10 assertions** (wiring source-guard)
  - `frontend/src/pages/aper/__tests__/sol_presenters_filter.test.js` — **9 assertions** (helpers purs)
- [x] `applyAperFilter` + `normalizeAperFilter` exportés : `frontend/src/pages/aper/sol_presenters.js:117, 148`

Intention A1 **entièrement couverte** par le HEAD actuel.

## 5. Test d'invariant F3 — que protège-t-il vraiment ?

Fichier : `frontend/src/__tests__/test_suites_invariant.test.js` (commit `97984b6c`).

### Invariants documentés
1. **`describe('<helper>', …)` d'une fonction importée ne doit apparaître que dans UN SEUL fichier test** — détection par paire `(identifier, stableImportKey)`.
   - `stableImportKey(importPath)` normalise le path (retire `..`/`.`, garde la partie stable après les sauts de dossier)
   - 8 doublons pré-existants whitelist (`LEGACY_DUPLICATES`) exempts tant qu'ils ne sont pas résorbés

### Le test protège-t-il contre :
- [ ] **Deux commits avec même message en peu de temps** → ❌ NON. Le test regarde l'état final du disque, pas l'historique git.
- [x] **Deux fichiers test chargeant le même module** (`AperSol.deep_link.test.js` ET `sol_presenters_filter.test.js` déclarent chacun `describe('normalizeAperFilter', …)` à partir du même `../sol_presenters`) → **OUI** — mais…
   - Au moment de F3, `AperSol.deep_link.test.js` avait été réduit aux seuls source-guards wiring (F3 commit `97984b6c` → − 78 lignes). Les `describe('normalizeAperFilter')` + `describe('applyAperFilter')` ont été supprimés de ce fichier. Le doublon sémantique a donc été résorbé côté F3.
- [ ] **Deux branches divergentes non-mergées** → ❌ NON. Le test ne lit pas l'historique git, uniquement les fichiers présents en HEAD.
- [x] **Autre** : détecte toute future tentative de redupliquer un `describe(helper)` pour la même fonction (anti-récidive structurelle).

### Conclusion
Le test d'invariant F3 **ne protège pas contre la cause racine de l'incident A1** (même message de commit à 51s d'écart). Il protège contre le **symptôme** (doublon de tests). Comme la cause racine était un cas de discipline humaine (je n'ai pas noté que je venais de committer 51s avant et j'ai créé un 2e commit avec le même subject), aucun test code-level ne pourrait raisonnablement l'attraper.

## 6. Verdict final

### Cas retenu
- [x] **CAS A étendu (A')** — séquentiel cumulatif, pas bifurcation. Le 2e commit (`75bc32c8`) est un commit normal enfant du 1er (`80d7121a`). Aucune divergence git, aucun fork, aucun besoin de merge. Le seul problème est **cosmétique** : les 2 commits partagent un même subject alors qu'ils avaient des intentions distinctes (le 1er livre le code + test wiring, le 2e ajoute une batterie de tests unitaires purs pour les helpers).

### Recommandation action
- **Push** : `git push -u origin claude/refonte-visuelle-sol` (HEAD `249a4ef9`). Risque nul.
- **Puis** : GO Sprint 1 Vague B.

### Test d'invariant — verdict protection
- Protège effectivement contre la bifurcation ? **NON** — scope différent, il cible la duplication de `describe(helper)` au niveau tests.
- Mais aurait attrapé la duplication réelle si elle était restée dans 2 fichiers (elle a été résorbée par F3 `97984b6c` en retirant les `describe('normalizeAperFilter')` et `describe('applyAperFilter')` de `AperSol.deep_link.test.js`).
- **Pas de lacune à combler** — le cas originel n'est pas techniquement une bifurcation, donc aucun test code-level n'aurait pu le détecter. Seul le process humain (messages de commit discriminants) peut prévenir.

## 7. Actions post-audit recommandées

- [x] **Push branche** (CAS A étendu — safe).
  ```bash
  git push -u origin claude/refonte-visuelle-sol
  ```
- [ ] ~~Cherry-pick correctif~~ — non pertinent (pas de CAS B).
- [ ] ~~Arbitrage user~~ — non pertinent (pas de CAS C).
- [ ] **Renforcer test d'invariant** — non nécessaire, la cause racine est humaine (discipline des messages de commit).
- [x] **Documenter l'incident** — ce rapport + note que le bilan Sprint 1 Vague A mentionnait à tort « bifurcation + fast-forward merge ». Correction : pas de bifurcation, juste 2 commits linéaires successifs avec message subject identique (mauvaise pratique cosmétique, pas un risque technique).

### Recommandation discipline (hors scope test code)
Pour Vague B, adopter un post-commit hook qui refuse deux commits consécutifs avec le même subject dans une fenêtre de 5 minutes — ou simplement relire `git log -1` avant chaque `git commit`. Pas critique.

---

## Annexe — Contenu du commit additif `75bc32c8`

Fichier créé : `frontend/src/pages/aper/__tests__/sol_presenters_filter.test.js` (68 L, 8 tests)
- `describe('normalizeAperFilter', …)` — 3 tests (accepts 'parking', 'toiture', rejects others → null)
- `describe('applyAperFilter', …)` — 5 tests (null → unchanged, parking → kept, toiture → kept, null dashboard → null, missing category → empty)

Ces tests sont **complémentaires** et non **redondants** avec ceux initialement présents dans `AperSol.deep_link.test.js` — le 1er fichier testait le wiring `AperSol.jsx` (source-guard regex), le 2e testait les helpers purs en isolation. F3 `97984b6c` a confirmé cette séparation en retirant de `AperSol.deep_link.test.js` les tests d'helpers purs qui y avaient été dupliqués par erreur dans le commit initial `80d7121a`.

En réalité `75bc32c8` a été l'étape qui a **corrigé** cette duplication en créant le fichier de tests dédié. Le vrai travail a été complété en 2 commits, simplement avec des messages peu discriminants.

_Rapport généré depuis arbre de travail `claude/refonte-visuelle-sol` HEAD `249a4ef9`, 2026-04-23._
