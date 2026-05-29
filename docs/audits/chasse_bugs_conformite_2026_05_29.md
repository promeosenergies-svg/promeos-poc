# Chasse-bugs Tour 1 — `/conformite`

**Date** : 2026-05-29
**Branche** : `claude/chasse-bugs-conformite-2026-05-29`
**Base** : `claude/refonte-sol2` HEAD `8cadab64` (post #332)
**Skill** : `chasse-bugs-promeos` (1er tour)

## Périmètre audité

- `frontend/src/pages/ConformitePage.jsx`
- `frontend/src/pages/conformite-tabs/{Obligations,Donnees,Execution,Preuves}Tab.jsx`
- `frontend/src/components/conformite/*.jsx`

## Findings par catégorie

### Cat 1 — Boutons / liens inactifs : 1 finding critique

**[CRITIQUE]** 3 boutons « Compléter le questionnaire » / « Compléter intake » naviguent vers `/intake/<siteId>` :
- `frontend/src/pages/ConformitePage.jsx:1125`
- `frontend/src/pages/conformite-tabs/DonneesTab.jsx:350`
- `frontend/src/pages/conformite-tabs/ObligationsTab.jsx:1174`

**Vérification** : aucune route `/intake` dans `frontend/src/App.jsx`. Aucune page `IntakePage*` dans `frontend/src/pages/`. → **404 silencieux à chaque clic** (l'utilisateur arrive sur une page blanche ou le redirect par défaut, perdant son contexte).

**Origine probable** : la page Intake était prévue dans un sprint produit antérieur, supprimée ou jamais livrée. Les CTA sont restés.

### Cat 2 — Routes mortes : 0 finding nouveau

`/conformite/tertiaire` existe et est correctement routée (ligne 270 d'App.jsx). Les CTA `navigate('/conformite/tertiaire')` sans `site_id` (ex `ObligationsTab:594` « Ouvrir OPERAT ») sont **légitimes** car c'est un CTA générique vers le dashboard OPERAT — pas une flèche par-ligne (qui elle exige le contexte site, déjà fixé S2 hotfix pour `DtProgressMultiSite`).

### Cat 3 — Jargon technique exposé : 0 finding

Aucune occurrence de `undefined / NaN / null / TODO / FIXME / rule_id / correlation_id / score_stale / [object Object]` dans les fichiers UI auditer. Vocabulaire technique correctement encapsulé dans `<Explain>` et tooltips.

### Cat 4 — Texte non-FR : 0 finding

Aucun string anglais rendu repéré. Vocabulaire FR cohérent.

### Cat 5 — « ? » indicatifs morts : 0 finding

- `MutualisationSection:420` `aria-label="Pourquoi ce chiffre ?"` ouvre bien `EvidenceDrawer` (vérifié).
- 4 icônes `<Info>` rencontrées dans ObligationsTab/MutualisationSection/ModulationDrawer sont décoratives (pas de pretention d'aide cliquable).

### Cat 6 — Calculs faux : 0 finding nouveau

Le hotfix S2 (-100 % artefact DT) est en place. Pas d'autre calcul FE détecté.

### Cat 7 — KPI mensongers : 0 finding nouveau

Aucun « 0 € » brut. `ConformiteSyntheseCompacte` carte 4 rend correctement « à qualifier » via `<Explain term="penalty_exposure">` quand `total_impact_eur === null`.

### Cat 8 — Console errors : pas testé ce tour

Reporté au tour Playwright dédié (déjà couvert par `golden-paths.spec.js` du sprint #329, 4/4 verts).

### Cat 9 — Network 4xx/5xx : pas testé ce tour

Idem, déjà couvert par `s2-conformite-simplicite-metier.spec.js` + `golden-paths.spec.js` (9/9 verts).

### Cat 10 — Dette technique : 0 finding nouveau

La dette `nav_v7_parity` 14↔13 a été résorbée PR #332. Aucune autre dette test/source-guard détectée sur ce périmètre.

## Décisions

| Finding | Décision | Action |
|---|---|---|
| Cat 1 — 3 CTA `/intake/<id>` cassés | **Fixer ce tour** (trivial, 3×~5 lignes) | Désactiver le bouton + tooltip FR explicite + commentaire renvoyant à ce doc |

**Pourquoi désactiver plutôt que router ailleurs** : aucune page de substitution n'a la même finalité (collecte de questionnaire BACS/audit énergétique guidée). Rerouter vers `/patrimoine` ou `/conformite?tab=donnees` créerait une promesse cassée différente. Désactiver + tooltip explicite est honnête.

**Pourquoi pas retirer les boutons** : l'analytics `track('bacs_complete_data')` et `track('conformite_goto_intake')` montre que l'équipe produit suit ces taux de clic. Garder le bouton visible mais désactivé permet de préserver le signal d'intention (« combien d'utilisateurs auraient voulu cliquer »).

## Verdict tour 1

✅ **GO** — 1 finding critique fixé (Cat 1), 0 régression, hub `/conformite` toujours cohérent.

## Suite (tour 2 selon skill)

`/usages` + composants (PilotageSourceBackLink, UsageSignalCard, etc.)
