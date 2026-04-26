# ADR-001 — Grammaire Sol industrialisée

**Statut** : Proposé
**Date** : 2026-04-26
**Sprint** : S1 (semaines 2-3)
**Personnes impliquées** : Amine (founder), Claude architect-helios

## Contexte

L'audit Sprint 0 (`memory/project_sprint0_audit_doctrine_synthese.md`) révèle un score doctrinal 4.2/10. Pattern récurrent #2 : seulement 2/10 pages utilisent `SolPageHeader`, 0/10 ont `SolPageFooter`, 0/10 ont week-cards typées. La grammaire éditoriale §5 de la doctrine (kicker → titre Fraunces → narrative 2-3l → 3 KPIs → week-cards → footer SCM) n'est pas industrialisée — chaque page la réinvente partiellement.

Sans grammaire industrialisée, S2-S6 produiront du polish désordonné. Il faut un kit éditorial canonique avant tout sprint feature.

Pattern récurrent #5 audit Sprint 0 : `RegulatoryCalendarCard`, `BriefCodexCard.buildBrief*`, `KpiStrip.ipe`, `utils/benchmarks.js` violent §8.1 règle d'or. La narrative et le footer SCM doivent venir backend, pas être recomposés en JSX.

## Décision

### Composants frontend canoniques `frontend/src/ui/sol/`

Quatre composants invariants, **PropTypes documentés**, **aucune logique métier** :

1. `SolPageHeader` (existe, à étendre) — props : `kicker: string` (mono Plex), `title: string` (Fraunces), `metadata: { source, confidence, updatedAt }`
2. `SolNarrative` (nouveau) — props : `kicker`, `title`, `narrative: string` (2-3 lignes pré-formatées backend), `kpis: [{ label, value, unit, tooltip, source }]` (max 3)
3. `SolWeekCards` (nouveau) — props : `cards: [{ type: 'watch'|'todo'|'good_news'|'drift', title, body, cta?, impact? }]` exactement 3 cards. Si backend renvoie <3, le composant insère un fallback densifié contextualisé (ex : "portefeuille stable cette semaine, 5 sites OPERAT à jour, prochaine échéance dans 68 jours") — anti-pattern §6.1 zéro vide
4. `SolPageFooter` (nouveau) — props : `source`, `confidence: 'high'|'medium'|'low'`, `updatedAt: ISO8601`, `methodology?: link`

### Backend — sources de vérité

**Narrative source** : nouveau service `backend/services/narrative/narrative_generator.py`
- Entry : `generate_page_narrative(org_id, page_key, persona, archetype, lang='fr') -> Narrative`
- Page keys : `cockpit_daily`, `cockpit_comex`, `patrimoine`, `conformite`, `bill_intel`, `achat`, `monitoring`, `diagnostic`, `anomalies`, `flex`
- Output dataclass `Narrative { kicker, title, narrative, kpis[3], week_cards[3], footer }`
- Branche P3 (Sprint 3) : injection archetype (cf ADR-003)
- Backend builders délégués aux services métier existants — orchestration uniquement, **pas** de calcul ici

**Footer SCM (Source · Confiance · Mis à jour)** : nouveau service `backend/services/data_provenance/provenance_service.py`
- Décorateur `@with_provenance(source, confidence_resolver)` appliqué aux endpoints REST des 7 piliers
- Réponse standard enveloppée : `{ data: ..., provenance: { source, confidence, updated_at, methodology_url } }`
- Niveaux confiance déterministes : `high` (calcul backend sourcé RegOps/ADEME/EPEX), `medium` (estimation modélisée), `low` (heuristique fallback)

### Réutilisation existant (inventaire Sprint 0bis)

L'inventaire Sprint 0bis a identifié **92% de l'infrastructure narrative déjà existante** :
- `frontend/src/models/dashboardEssentials.js` (8 fonctions buildWatchlist/buildBriefing/buildOpportunities/buildTodayActions)
- `frontend/src/models/priorityModel.js` (buildPriority1)
- `frontend/src/pages/cockpit/BriefingHeroCard.jsx` + `WatchlistCard.jsx` + `OpportunitiesCard.jsx`

`narrative_generator.py` orchestre ces sources existantes côté backend (élimine §8.1 violation), expose endpoint unique pour 8 nouvelles pages.

### Endpoint contrat unique

`GET /api/pages/{page_key}/briefing?org_id=X&persona=daily|comex&archetype?=auto|tertiaire|industriel|hotelier|collectivite|mono_site`
Retourne `Narrative` complet (header + 3 KPIs + 3 week-cards + footer). Org-scoping via `resolve_org_id` obligatoire.

### Routing

Collapse `/` → `/cockpit?angle=daily` via redirect 301. Une seule home doctrinale (§4.7). Élimine source-vérité multiple #6 (2 gauges patrimoine `/` vs `/cockpit`). Route `/` legacy à supprimer en S6.

### Migration plan 8 pages

Ordre, gated par tests source-guards :
S1.1 Cockpit daily + COMEX (ouvre la voie) → S1.2 Patrimoine + Conformité → S1.3 Bill-Intel + Achat → S2 (parallèle α) Monitoring + Diagnostic + Anomalies + Flex.

Chaque page = un PR atomique avec template §11.3 doctrine compliance.

### Tests source-guards `backend/tests/source_guards/test_grammar_sol.py`

- `test_no_business_logic_in_jsx` : grep `frontend/src/pages/sol/` pour patterns interdits (`*calculate*`, `*compute*`, hardcoded ADEME/RegOps constants, `Math.*` métier)
- `test_every_page_has_briefing_endpoint` : pour chaque `page_key`, vérifier endpoint répond + payload conforme schéma `Narrative`
- `test_provenance_envelope` : tout endpoint des 7 piliers retourne `provenance` non null
- `test_week_cards_never_empty` : si <3 cards remontées, fallback densifié présent (anti-pattern §6.1)
- `test_no_raw_acronyms_in_titles` : titres narrative ne contiennent aucun acronyme du dictionnaire ADR-004 (DT/BACS/APER/...)

## Conséquences

- **Positives** : grammaire invariante testable, narrative backend = SoT unique, footer SCM systématique = crédibilité B2B, fallback densifié élimine empty states, collapse `/` → `/cockpit` règle source-vérité multiple
- **Négatives / risques** : narrative_generator devient point de centralisation dense — risque god-service. Mitigation : orchestration only, builders délégués aux services pillar
- **Migration** : 8 PRs atomiques sur S1-S2, chaque PR migre 1 page + ajoute test source-guard. Route `/` redirect 301 maintenue 6 semaines puis supprimée S6

## Alternatives considérées

1. **Hooks frontend qui composent narrative côté client** — rejeté : viole §8.1 règle d'or, recompose la divergence
2. **Conserver `/` distinct du cockpit** — rejeté : audit Sprint 0 #6 source vérité multiple, doctrine §4.7 = un seul cockpit
3. **PropTypes legacy vs migration TypeScript intégrale** — différé : PropTypes documentés en S1, migration TS reportée S6+ (hors scope démo juillet)

## Tests / validation

Tests doctrinaux 1, 4, 7 validés au merge S1 sur les 8 pages. T1 (3 secondes) audité Playwright captures avant/après. T4 (densité) garanti par test `test_week_cards_never_empty`. T7 (transformation acronymes) garanti par `test_no_raw_acronyms_in_titles` (lié ADR-004).

## Doctrine compliance §11.3

- **Principes respectés** : 1 (briefing), 4 (densité éditoriale), 8 (simplicité iPhone-grade), 9 (chaque brique vaut un produit), 11 (bon endroit)
- **Anti-patterns évités** : §6.1 empty states, §6.5 logique frontend, §6.4 source vérité multiple
- **Personas servis** : Marie (briefing daily), Jean-Marc (COMEX), investisseur (cohérence éditoriale 8 pages)

## Référence cross-ADR

ADR-002 (chantier α alimente `week_cards` du briefing endpoint), ADR-003 (chantier β branche `archetype` du narrative_generator), ADR-004 (chantier δ alimente le dictionnaire de transformation acronymes utilisé par narrative_generator). Memory : `project_refonte_sol_doctrine_3mois.md`, `project_sprint0_audit_doctrine_synthese.md`. Doctrine §5, §8.1, §9.3.

## Délégations sortantes

- Implémentation S1 : `implementer` (chaîné `test-engineer` + `code-reviewer` + `qa-guardian` pre-merge)
- Tests source-guards : `test-engineer`
- Validation org-scoping endpoints : `security-auditor`
