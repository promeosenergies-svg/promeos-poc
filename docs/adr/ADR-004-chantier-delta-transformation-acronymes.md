# ADR-004 — Chantier δ transformation acronymes systématique

**Statut** : Proposé
**Date** : 2026-04-26
**Sprint** : S3 (parallèle β, semaines 6-7)
**Personnes impliquées** : Amine (founder), Claude architect-helios

## Contexte

Pattern audit Sprint 0 #3 : acronymes bruts en titres systématiques sur 7 piliers — DT, BACS, APER, OPERAT, TURPE 7, CTA, NEBCO, ARENH, VNU, EUI, DJU, CUSUM, TICGN, aFRR, AOFD. Anti-pattern §6.3 doctrine. Test T7 (transformation) FAIL universel.

**Inventaire Sprint 0bis** : glossaire/transformation δ couvert à **88% déjà existant** :
- `frontend/src/ui/glossary.js` (65+ termes : sous_compteur/turpe/atrd/accise/cspe/cta/tva/car/tdn/cee/vnu/capacite/ht/ttc, sources CRE/Code Impositions/LFI 2026)
- `frontend/src/ui/Explain.jsx` (composant inline tooltip a11y, utilisé 65+ fois cockpit/conformité/billing/achat)
- 4 skills `.claude/skills/promeos-regulatory/`, `regulatory_calendar/`, `regops_constants/`, `energy-france-veille/`
- `audit/v5/phase05_glossary_terms_finalized.md` (120+ termes audités)

**Le travail S3 δ est : (1) migrer glossaire frontend → backend SoT unique, (2) systématiser via test source-guard pytest, (3) compléter narratives 3 niveaux par terme.**

Composant `<Explain>` existe partiellement — sans glossaire structuré ni source unique. Risque sans systématisation : chaque PR S1-S5 réintroduit acronymes dans titres → score doctrine plafonne.

Principe 10 (transformer la complexité en simplicité) — **transformer**, pas cacher ni exposer.

## Décision

### Source unique `backend/services/glossary/term_definitions.py`

Dictionnaire structuré canonique. Chaque terme :
```python
@dataclass
class GlossaryTerm:
    acronym: str                  # "DT"
    full_form: str                # "Décret Tertiaire"
    short_narrative: str          # "trajectoire 2030 obligatoire"  (≤ 6 mots, pour titres)
    medium_narrative: str         # "obligation -40% conso d'ici 2030 sur bâtiments tertiaires >1000 m²"  (≤ 25 mots, pour week-cards)
    long_narrative: str           # paragraphe complet pour modal Explain (≤ 80 mots)
    legal_source: str             # "Décret n°2019-771"
    legal_url: str
    pillar: enum                  # regops | bill_intel | ems | flex | achat | patrimoine
    related_terms: list[str]      # ["BACS", "OPERAT", "APER"]
    archetype_relevance: dict     # { TERTIAIRE_MIDMARKET: 'critical', INDUSTRIEL_AGROALIM: 'low', ... }
```

Stockage : `backend/config/glossary.yaml` (ParameterStore versionné). Source unique consultée par narrative_generator (ADR-001), event detectors (ADR-002), composant Explain frontend.

**Migration** : porter les 65 termes existants de `frontend/src/ui/glossary.js` vers `backend/config/glossary.yaml`. Frontend `Explain.jsx` consomme via endpoint `/api/glossary/{term}` au lieu du dict local. Source-guard pytest interdit toute redéfinition frontend.

### Liste canonique S3 — 15 termes minimum

Chaque terme produit ses 3 narratives (court / moyen / long) avant merge ADR-004 :

| Acronyme | short_narrative |
|----------|-----------------|
| DT | "trajectoire 2030 obligatoire" |
| BACS | "GTB obligatoire bâtiments 2027" |
| APER | "audit énergétique 4 ans" |
| OPERAT | "déclaration annuelle conso" |
| Audit SMÉ | "audit obligatoire 11/10/2026" |
| TURPE 7 | "tarif acheminement réseau" |
| CTA | "contribution acheminement gaz" |
| NEBCO | "rémunération de la flexibilité" |
| ARENH | "ancien tarif nucléaire historique" |
| VNU | "remplaçant ARENH 2026+" |
| EUI | "intensité énergétique m²" |
| DJU | "rigueur climatique annuelle" |
| CUSUM | "détection dérive consommation" |
| TICGN | "accise gaz" |
| aFRR | "réserve réglage secondaire RTE" |
| AOFD | "appel d'offres effacement" |

Extensible — toute PR ajoutant un terme exposé en UI doit déclarer entrée glossary.

### Composant `<Explain>` étendu frontend

`frontend/src/ui/sol/Explain.jsx` (existe partiel à généraliser) :
- Props : `term: string` (lookup glossaire backend)
- Affichage : badge `?` discret, hover/click ouvre modal avec `medium_narrative` + lien `legal_url` + related_terms
- Hook `useGlossary(term)` appelle `GET /api/glossary/{term}` (cache localStorage 24h)
- Aucune définition dure-codée frontend — toute valeur vient backend

### Règle copy invariante

**Aucun acronyme nu en `<h1>`, `<h2>`, titre carte, kicker, ou label KPI.**

Forme canonique :
- Titre Sol : `short_narrative` directement, **ou** `Décret Tertiaire — trajectoire 2030`
- Body week-card : `medium_narrative` + `<Explain term="DT">`
- Modal/drill-down : `long_narrative` + source légale

### Endpoint contrat

`GET /api/glossary/{term}` → `GlossaryTerm` complet
`GET /api/glossary?pillar=regops&archetype=tertiaire_midmarket` → liste filtrée triée par relevance

### Test source-guard pytest `tests/source_guards/test_no_raw_acronyms.py`

Critique pour non-régression :
```python
RAW_ACRONYMS = {"DT", "BACS", "APER", "OPERAT", "TURPE 7", "CTA", "NEBCO",
                "ARENH", "VNU", "EUI", "DJU", "CUSUM", "TICGN", "aFRR", "AOFD"}

def test_briefing_endpoints_no_raw_acronyms_in_titles():
    for page_key in ALL_PAGE_KEYS:
        for archetype in ALL_ARCHETYPES:
            briefing = get_briefing(page_key, archetype)
            assert not contains_raw_acronym(briefing.title, RAW_ACRONYMS)
            for card in briefing.week_cards:
                assert not contains_raw_acronym(card.title, RAW_ACRONYMS)
```

Whitelist autorisée : si l'acronyme est immédiatement suivi d'un tiret + narrative (`"DT — trajectoire 2030"`), ou si présent dans `legal_source` cité, ou dans body inline avec `<Explain>` adjacent.

### Migration plan

S3.1 : YAML glossaire 15 termes + endpoint + tests source-guards (failing → bloque toute PR S3+ qui exposerait acronyme nu)
S3.2 : audit grep automatisé du codebase frontend `frontend/src/pages/sol/` détectant acronymes restants → tickets atomiques par pilier
S3.3 : refactor 7 piliers — chaque PR pilier inclut migration acronymes + lien Explain. Échec source-guard = blocage merge

## Conséquences

- **Positives** : T7 (transformation) PASS sur 7 piliers, principe 10 incarné, crédibilité B2B renforcée (source légale visible), source unique élimine variations copy
- **Négatives / risques** : 15 termes × narratives 3 niveaux × 5 archetypes relevance = travail rédactionnel dense. Mitigation : narratives par défaut archetype-agnostiques, override ciblé seulement quand pertinent. Risque source-guard trop strict bloquant légitime ("Décret Tertiaire" suffit-il ?). Mitigation : whitelist explicite tirets-narrative
- **Migration** : couplée à S3 (parallèle β) car narrative_generator et glossary_service partagent infra ParameterStore

## Alternatives considérées

1. **Tooltip natif HTML title=** — rejeté : non-stylable, non-accessible, non-trackable, ne distingue pas non-sachant/sachant
2. **Glossaire frontend hardcoded JSON** — rejeté : viole §8.1 + duplication entre narrative et glossaire
3. **LLM rewriting on-the-fly** — rejeté : non-déterministe, coût, latence. Pour démo investisseur on veut copy exactement reproductible

## Tests / validation

- T7 (transformation) automatisé : `test_no_raw_acronyms_in_titles` (CI obligatoire, blocking)
- `test_glossary_yaml_schema_complete` : tous termes ont 3 narratives + source légale
- `test_explain_component_uses_backend` : grep frontend, aucune définition acronyme dure-codée
- Test E2E Playwright : sur Cockpit + Conformité + Bill-Intel, hover/click sur Explain ouvre modal + affiche narrative + lien source légale fonctionnel
- Test doctrine T7 manuel : un dirigeant non-sachant lit titre Sol et comprend sans cliquer

## Doctrine compliance §11.3

- **Principes respectés** : 8 (simplicité iPhone-grade), 10 (transformation), 12 (non-sachant servi)
- **Anti-patterns évités** : §6.3 acronymes bruts dans titres, §6.3 tooltip qui répète sans définir, §6.5 source vérité multiple (glossaire = SoT unique)
- **Personas servis** : Marie (titres compréhensibles sans formation), Jean-Marc (drill source légale en 1 clic), investisseur (démo "produit pour non-sachants" prouvée)

## Référence cross-ADR

ADR-001 (narrative_generator consomme glossary pour composer titres), ADR-002 (event detectors stockent `title` déjà transformé via glossary lookup), ADR-003 (archetype_relevance influence sélection terms par archetype). Memory : `reference_veille_reglementaire_2025_2026.md`, `reference_regulatory_landscape_2026_2050.md`, `agent_veille_reglementaire.md`. Doctrine §3 P10, §6.3, §9.3 chantier δ.

## Délégations sortantes

- Implémentation S3 : `implementer` (chaîné `test-engineer` + `code-reviewer` + `qa-guardian` pre-merge)
- Validation contenu narratives + sources légales : `regulatory-expert`
- Validation invariants frontend : `code-reviewer` (read-only)
