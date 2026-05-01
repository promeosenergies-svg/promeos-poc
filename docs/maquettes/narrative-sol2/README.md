# Kit Sprint Narrative dynamique Synthèse stratégique — guide d'injection Claude Code

> **Statut** : kit complet livré 2026-05-01 · cibles validées Amine après audit
> `AUDIT_NARRATIVE_DYNAMIQUE.md`.
>
> **Usage** : injecter ces 4 fichiers dans Claude Code aux côtés du prompt
> d'exécution pour que Claude Code dispose de la référence visuelle pixel-perfect
> à chaque phase du sprint.

## Fichiers du dossier

| Fichier | Rôle |
|---|---|
| `narrative-grand-groupe.html` | Maquette typologie Grand groupe tertiaire — 7 variantes (6 triggers + stable) |
| `narrative-commerce.html` | Maquette typologie Commerce/commerçant — 7 variantes |
| `narrative-erp.html` | Maquette typologie Établissement recevant du public — 7 variantes |
| `PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md` | Sprint exécution 6 phases · 4-5 semaines |
| `README.md` | Ce fichier |

## Comment injecter dans Claude Code

### Étape 1 — Copier dans le repo

```bash
cd promeos-energies
mkdir -p docs/maquettes/narrative-sol2
cp /chemin/vers/maquettes/*.html docs/maquettes/narrative-sol2/
cp /chemin/vers/maquettes/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md docs/maquettes/narrative-sol2/
cp /chemin/vers/maquettes/README.md docs/maquettes/narrative-sol2/
git add docs/maquettes/narrative-sol2/
git commit -m "docs(maquettes): narrative dynamique sol2 — 3 typologies + sprint exécution validé Amine 2026-05-01"
```

### Étape 2 — Référencer dans la session Claude Code

Au début de chaque session :

> Avant de coder, ouvre `docs/maquettes/narrative-sol2/narrative-grand-groupe.html`,
> `narrative-commerce.html`, `narrative-erp.html`. Lis le `README.md` et le
> `PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`. Ces fichiers sont la cible
> visuelle de fin de Phase 4 du sprint Narrative dynamique. Tout composant
> que tu créeras doit converger vers cette cible.

## Mapping composants/phases attendu

### Phase 1 — Typologie organisationnelle

| Composant à créer | Phase | Maquette de référence |
|---|---|---|
| `backend/doctrine/naf_to_typology.py` | Phase 1.1 | n/a (backend) |
| `backend/services/narrative/typology_resolver.py` | Phase 1.2 | n/a (backend) |
| `backend/services/narrative/lexical_templates.py` | Phase 1.3 | les 3 maquettes (vocabulaire) |
| `backend/models/user_preference.py` (override) | Phase 1.4 | n/a |

### Phase 2 — Push événementiel

| Composant | Phase | Cible visuelle |
|---|---|---|
| `backend/services/narrative/event_push.py` | Phase 2.1 | Variante 3 (push +18 % vs S-1) |
| Modification `narrative_generator.py` injection | Phase 2.2 | Toutes variantes activées |

### Phase 3 — Hiérarchisation déclencheurs

| Composant | Phase | Cible visuelle |
|---|---|---|
| `backend/doctrine/triggers.py` (6 triggers + priorités) | Phase 3.1 | n/a |
| `backend/services/narrative/trigger_prioritizer.py` | Phase 3.2 | n/a |
| `backend/services/narrative/sentence_composer.py` | Phase 3.3 | Variantes 1-6 (phrase 1 différente par typologie) |

### Phase 4 — Persona + tonalité

| Composant | Phase | Cible visuelle |
|---|---|---|
| `backend/services/narrative/persona_context.py` | Phase 4.1 | Mention italique en bas de chaque variante |
| `backend/services/narrative/tone_variator.py` | Phase 4.2 | Variantes alarme vs stable (lexique différent) |

### Phase 5 — Validation panel humain

Pas de composant code. 6 sessions humaines + 6 verbatims + ajustements éditoriaux finaux.

### Phase 6 — `simulate_date`

| Composant | Phase | Cible visuelle |
|---|---|---|
| Modification `narrative_generator.build_briefing` | Phase 6.1 | Test J vs J+30 |

## Règles de divergence acceptable

Pendant la refonte, ces écarts entre maquettes et production sont **acceptables** :

1. **Données dynamiques** : maquettes = HELIOS hardcodé en démo, production = vraies
   données via API
2. **Mode sombre** : maquettes en light only, production hérite du Sol design system
3. **Animation entrance** : maquettes statiques, production avec micro-animations Sol
4. **Responsive** : maquettes 1280 px+ desktop, production responsive

## Règles de divergence NON acceptable

Les écarts suivants sont **bloquants** :

1. **Vocabulaire typologique** : Grand groupe doit contenir "patrimoine", "CODIR".
   Commerce ne doit JAMAIS contenir "patrimoine" ni "CODIR". ERP doit contenir
   "établissement", "usagers" / "élèves" / "résidents".
2. **Aucun acronyme en body** : "DT", "BACS", "GTB", "TURPE", "APER" interdits dans
   le body narrative. Seul le footer porte le sourçage réglementaire complet.
3. **Push événementiel strict** : variation < 5 % OU < 1 k€ → silence éditorial,
   jamais de push.
4. **Max 1 primary trigger + 1 secondary** dans le body (Option 4.C), même si
   plusieurs triggers actifs simultanément.
5. **Mention persona italique** présente dans toute variante avec utilisateur
   connecté (sauf rendu anonyme).
6. **Footer sourçage** systématique sur toute narrative.

## Anti-patterns à NE PAS introduire

- ❌ Acronyme "DT", "BACS", "TURPE" en body narrative
- ❌ Vocabulaire "patrimoine" dans typologie commerce
- ❌ Vocabulaire "CODIR" dans typologie commerce ou ERP (ERP utilise "comité de direction")
- ❌ Push +0,2 k€ vs S-1 (sous seuil silence éditorial)
- ❌ 3+ triggers tissés dans body narrative (max 2 selon Option 4.C)
- ❌ Mention persona dans le footer (doit être dans le body en italique)
- ❌ Sourçage réglementaire dans le body (doit être en footer)

## Doctrine compliance — Synthèse §11.3

Les 9 cibles doctrine §11.3 que ce sprint doit valider :

- [ ] Cible 1 : Lecture 3 min CFO — narrative ≤ 80 mots
- [ ] Cible 2 : Hiérarchisation 1ère phrase — primary trigger en phrase 1
- [ ] Cible 3 : Sourçage réglementaire — footer systématique
- [ ] Cible 4 : Signal saillant — push événementiel quand actif
- [ ] Cible 5 : 3 typologies organisationnelles — MVP grand groupe / commerce / ERP
- [ ] Cible 6 : 6 déclencheurs hiérarchisés — primary + secondary maximum
- [ ] Cible 7 : Mention persona — italique en fin de body
- [ ] Cible 8 : Variation tonale — exploitation `narrative_tone` calculé
- [ ] Cible 9 : Acronymes glossés — aucun acronyme brut en body, sourçage en footer

## Changelog

| Date | Changement | Trigger |
|---|---|---|
| 2026-05-01 | v1.0 — kit complet sprint Narrative dynamique | Audit `AUDIT_NARRATIVE_DYNAMIQUE.md` validé Claude externe + 5 décisions cadrage Amine validées |

---

**Maquettes Narrative dynamique Sol2 — méthodologie PROMEOS doctrine §11.3 + arbitrages Amine 2026-05-01**
