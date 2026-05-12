# ADR-022 — Cockpit Jour : data sources canoniques (zero hardcode)

**Statut** : Accepté
**Date** : 2026-05-12
**Sprint** : Phase 3.4-bis F.15
**Auteurs** : Amine + Claude
**Supersede** : aucune (étend ADR-021 Hub Page Grammar L11)

---

## Contexte

L'audit user F.14 a révélé que **chaque chiffre de la page Cockpit Jour est
hardcodé** dans `backend/routes/cockpit.py` (KPIs, baseline 6,5 MWh/j, séries
HP/HC, pic 528 kW, puissance souscrite 1 500 kW, textes hero, highlights
Top 3). Cela viole 3 règles cardinales de la doctrine PROMEOS :

1. **Fiabiliser** (5 verbes Sol v1.1) — un chiffre sans source vérifiable n'est
   pas fiable.
2. **SoT unique** (CLAUDE.md §règles non-négociables) — `consumption_unified_service`
   est SoT consommation, mais le cockpit ne l'appelle pas.
3. **Zéro business logic frontend** — application correcte ; mais le backend
   réplique les chiffres en dur, ce qui crée un BL backend masqué non testable.

Le user dirige cardinal : « LA BASELINE doit être calculée et vérifiée en
fonction du patrimoine, les HP/HC en fonction du paramétrage contrat ; tous
les indicateurs, chiffres, courbes, histogramme, références doivent venir de
la réglementation, des contrats, des mesures et de paramétrage onboarding. »

---

## Décision

**Tout indicateur affiché sur Cockpit Jour doit dériver d'une source canonique
documentée. Aucun hardcode toléré (sauf fallback explicite type "données
partielles").**

### Matrice SoT par élément cockpit

| Élément | SoT canonique | Service / modèle | Statut |
|---|---|---|---|
| **Hero — count "3 signaux"** | computed depuis highlights P1+P2 | `cockpit_highlights_service.build_top_n(scope, n=3)` | À créer (F.19) |
| **Hero — texte narratif** | template dérivé top 3 highlights | `cockpit_hero_narrative.generate(highlights, scope)` | À créer (F.19) |
| **Hero — meta quality 98 %** | `consumption_unified_service.get_data_quality(scope)` | service existe partiellement | À étendre |
| **Hero — meta confiance** | dérivé qualité + ancienneté mesures | même service | À étendre |
| **Hero — meta scope (5 sites)** | `Σ sites_for_org_query(scope)` filtré is_demo | existe (F.14c) | OK |
| **KPI 1 — Conso mois courant (MWh)** | `consumption_unified_service.get_org_consumption(scope, period=current_month)` | service existe (fallback hardcoded 16,6) | À fiabiliser |
| **KPI 1 — delta vs N-1 (-6,9 %)** | même service période = N-1 même mois | non câblé | À créer |
| **KPI 2 — Conso J-1 (MWh)** | `consumption_unified_service.get_org_daily(scope, date=J-1)` | granularité jour non exposée | **À créer** |
| **KPI 2 — référence (6,5 MWh/j)** | `consumption_baseline_service.get_dju_adjusted_daily_baseline(scope)` | service inexistant | **À créer** |
| **KPI 3 — Pic puissance (kW)** | `consumption_unified_service.get_org_peak(scope, date=J-1)` = max(CDC 30 min) | service inexistant | **À créer** |
| **KPI 3 — Souscrite (kW)** | `Σ Compteur.puissance_souscrite_kw` du scope | colonne existe | **À câbler** |
| **KPI 3 — % atteint** | pic / souscrite × 100 | computed | OK |
| **Chart bars — 7 valeurs jour** | `consumption_unified_service.get_org_daily_range(scope, period=last_7d)` | granularité jour non exposée | **À créer** |
| **Chart bars — baseline** | même que KPI 2 (cohérence cross-widget) | `consumption_baseline_service` | **À créer** |
| **Chart bars — tone (crit/warn/pos)** | rule-based vs baseline : >×1.5 = crit, >×1.2 = warn, else neutral | `regops/scoring.classify_tone(value, baseline)` | **À ajouter** |
| **Chart bars — annotation (+72 %)** | computed depuis worst day vs baseline | service highlights | computed |
| **Chart line — série 24h kW** | `consumption_unified_service.get_org_hourly(scope, date=J-1)` | granularité horaire non exposée | **À créer** |
| **Chart line — plages HP/HC** | `ContractEnergy.tariff_periods` (matrice patrimoine §4.4.G #G-22) OU fallback TURPE 6 `config/tarifs_reglementaires.yaml` | **modèle à enrichir** | **À créer** |
| **Chart line — threshold souscrite** | même que KPI 3 souscrite | computed | OK |
| **Chart line — peak annotation** | max(hourly series) | computed | OK |
| **Chart line — hc_zones background** | dérivé des plages HP/HC du contrat | renderer reçoit `hc_zones[]` | **À câbler** |
| **Highlights Top 3** | `cockpit_highlights_service.build_top_n()` agrège : | À créer (F.19) | |
| → anomalies conformité DT/BACS/APER | `compliance_score_service.detect_anomalies(site)` | existe | À brancher |
| → anomalies facture R01-R31 | `bill_intelligence.detect_anomalies_for_invoice` | existe (phase L17 OK) | À brancher |
| → anomalies données EMS (staleness) | `EmsStalenessDetector.detect(scope)` | **inexistant** | **À créer** |
| → priorisation P1/P2/P3 | `regops/priority_scoring.compute_finding_priority` | extension `patrimoine_impact.compute_priority_score` | **À créer (F.19a)** |

### Algorithme de priorisation (F.19a)

Le score d'une finding (highlight candidate) est computed par
`regops/priority_scoring.compute_finding_priority` selon 5 dimensions
pondérées, alignées sur la doctrine PROMEOS (5 verbes : centraliser,
fiabiliser, comparer, auditer, piloter) :

| Dimension | Poids max | Justification doctrinale |
|---|---|---|
| **Sévérité** | 60 pts | Hérité `patrimoine_impact._SEV_BASE` : CRITICAL=60, HIGH=50, MEDIUM=30, LOW=10 |
| **Impact financier** (€/an) | 40 pts | Buckets log : >50 k€ = 40, 10-50 k€ = 30, 1-10 k€ = 20, sinon 0 (focus Marie/CFO) |
| **Urgence** (deadline) | 50 pts | <30j = 50, <90j = 35, <365j = 20, <730j = 10, sinon 0 (focus régulatoire calendar 2026-2030) |
| **Effet de levier** (scope) | 30 pts | GROUP = 30, PORTFOLIO = 20, SITE = 10 (focus Yannick/DG vision groupe) |
| **Domaine doctrinal** | 20 pts | PLATFORM_HEALTH = 20, COMPLIANCE = 18, FINANCIAL = 15, ENERGY = 12, OPTIMISATION = 8 (data fiable PASSE AVANT décisions — anti-pattern "conclusions sur données pourries") |

**Score total** ∈ [0, 200].

**Tiering** (mapping vers P1/P2/P3 affichés) :
- **P1** si score ≥ 130 — action critique sous 30 jours
- **P2** si score ≥ 80 — alerte action sous 90 jours
- **P3** si score ≥ 40 — veille / recommandation
- Sinon non affiché dans le briefing du jour

### Personas mapping

Le scoring privilégie les findings utiles pour les 3 personas démo :

- **Marie (DAF/CFO)** — favorisée par impact financier (40 pts) + compliance (18 pts)
- **Yannick (DG)** — favorisé par scope GROUP (30 pts) + urgence régulatoire (50 pts)
- **Asset/Energy manager** — favorisé par platform_health (20 pts) + sévérité (60 pts)

Un highlight P1 doit pouvoir être justifié pour chacun des 3 personas
(test doctrinal : « pourquoi Marie / Yannick / l'energy manager s'en
soucient-ils ? »).

### Anti-patterns interdits

1. **Hardcoder un chiffre KPI** dans `routes/cockpit.py` sans appel service.
2. **Présenter une conclusion** (« week-end concentre l'écart +72 % ») si la
   qualité données < 80 % (data_quality_gate doit gater la narration).
3. **Afficher une référence** (« référence 6,5 MWh/j ») sans audit trail
   (computed_at, scope, method).
4. **Sortir un highlight P1** sans `evidence` chiffrée + lien vers preuve.

---

## Roadmap d'implémentation

**Option 2 retenue par user** (démo investisseur first) :

| Phase | Périmètre | Effort | Livraison |
|---|---|---|---|
| **F.15** | ADR-022 (ce doc) | 0,5 j/h | **OK (livré)** |
| **F.19a** | `regops/priority_scoring.py` (algo canonique) | 1,5 j/h | À démarrer |
| **F.19b** | `services/cockpit_highlights_service.py` (aggregator) | 2 j/h | F.19a |
| **F.19c** | wire cockpit.py + générateur narratif hero | 2 j/h | F.19b |
| **F.16** | granularité daily/hourly/peak dans consumption_unified_service | 4 j/h | non-bloquant démo |
| **F.17** | wire KPIs + charts au service consumption | 3 j/h | F.16 |
| **F.18** | ContractEnergy.tariff_periods + plages HP/HC dynamiques | 5 j/h | F.16 |

Une fois F.19 livré, la démo investisseur affiche un Top 3 priorités
**vraiment calculé** depuis les anomalies réelles (compliance + billing +
EMS), avec scoring transparent et tiering P1/P2/P3 justifié.

---

## Conséquences

### Positives
- Aucune capture cockpit ne peut plus mentir : chaque chiffre a un trail.
- Le scoring P1/P2/P3 devient testable (unit tests par dimension).
- Les 3 personas voient la valeur dans chaque highlight P1.
- Aligné sur Doctrine v1.3 (« comprendre, décider, agir, prouver »).

### Négatives / risques
- Effort total ~18-25 j/h pour le câblage complet (F.16-F.19).
- La granularité daily/hourly de `consumption_unified_service` n'existe pas
  encore — les KPIs J-1 + charts dépendent de F.16.
- Pendant la transition, certains widgets affichent encore des fallbacks
  explicites « données partielles » (acceptable doctrinalement).

### Tests requis
- Source-guard : `routes/cockpit.py` ne doit plus contenir de literal kWh/MWh
  hardcodé (sauf fallback `if service.returns_empty: return placeholder`).
- Unit tests `priority_scoring` : 1 test par dimension + 5 tests d'intégration
  par persona.
- Test E2E : les 3 highlights affichés correspondent au top 3 du scoring.

---

## Références
- ADR-021 Hub Page Grammar L11 (composants `grammar/hub/*`)
- `CLAUDE.md` § règles non-négociables (zero BL frontend, SoT consumption)
- `reference_patrimoine_parametrage_matrice_v1_2026_05_03.md` §4.4.G ContractEnergy
- `project_promeos_vision_consolidee_v1_3_2026_05_08.md` (5 verbes, personas)
- `backend/services/patrimoine_impact.py` (`compute_priority_score` socle)
