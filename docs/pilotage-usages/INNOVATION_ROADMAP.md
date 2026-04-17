# Innovation Roadmap — Pilotage PROMEOS post-S22

**Objectif** : faire du module Pilotage "le meilleur au monde" en exploitant les **vraies données signal** (ENTSO-E, Tempo, Enedis CDC) pour créer des cas d'usage que ni Voltalis, ni NW, ni les GTB Flex Ready® ne font aujourd'hui.

**Socle acquis (S17-S22 + V1 Q2 2026)** : doctrine Pilotage, fenêtres J+7, 7 quick wins, pipeline RTE Tempo + ENTSO-E + APScheduler, Flex Ready® NF EN IEC 62746-4, TURPE 7 HC saisonnalisés, calibrage Enedis 2024, Radar prix négatifs J+7 + ROI Flex Ready® + Scoring portefeuille multi-sites + cartes Cockpit V1 (PR #222).

## État d'avancement (17/04/2026)

| PR | Périmètre | Statut | Tests |
|---|---|---|---|
| **#222** | Pilotage V1 Innovation — 3 endpoints (radar-prix-negatifs, roi-flex-ready/{site_id}, portefeuille-scoring) + 3 cartes Cockpit | ✅ mergée | 24/24 verts |
| **#227** | Option C — wiring Site model réel (`archetype_code` + `puissance_pilotable_kw`) | 🟡 en review | 32/32 verts · simplify 3-agents passé |
| **#229** | Sprint 1 P0 UX — CTAs + scope switcher + wording "NEBCO"→"Effacement rémunéré" + TZ Europe/Paris forcée | 🟡 en review | 10/10 source-guard · /simplify + /review appliqués |

Pointeurs mémoire :
- `memory/project_pilotage_v1_innovation.md` — détail V1 backend + frontend (commits 7300ffc7 + cce6546a + 307c8c78)
- `memory/project_pilotage_sprint1_p0_ux.md` — détail Sprint 1 UX P0

## 8 pistes ambitieuses par ordre de séquençage

### Vague 1 — Q2 2026 (zéro dépendance externe, impact cockpit)

**1. Radar prix négatifs J+7 (alertes proactives)** ✅ livré PR #222
- Modèle ML léger (gradient boosting) sur historique ENTSO-E + météo + PV installé
- Prédit les 513h/an de prix négatifs à J+7
- Cockpit : "3 fenêtres négatives probables cette semaine — déclenchez vos ECS/VE"
- **Effort** : 4-5 j/dev · ✅ livré PR #222 · **Impact** : wedge unique (agrégateurs voient H-1, nous voyons J+7) · **Dépend** : Open-Meteo gratuit
- **Livraison** : endpoint `/api/pilotage/radar-prix-negatifs` + carte Cockpit `RadarPrixNegatifsCard`
- **Follow-up** : Option C (PR #227) wire Site model réel · Sprint 1 UX (PR #229) CTAs + scope switcher

**2. ROI Flex Ready® chiffré par site** ✅ livré PR #222
- Au-delà du signal conforme NF EN IEC 62746-4, calcul du **gain € annuel**
- Évitement pointe + valorisation NEBCO spread + CEE BACS
- Transforme un standard coché en business case CFO
- **Effort** : 3 j · ✅ livré PR #222 · **Impact** : aucun concurrent ne chiffre · **Dépend** : grille TURPE 7 + spread NEBCO historique
- **Livraison** : endpoint `/api/pilotage/roi-flex-ready/{site_id}` + carte Cockpit `RoiFlexReadyCard`
- **Follow-up** : Option C (PR #227) wire Site model réel · Sprint 1 UX (PR #229) CTAs + scope switcher

**3. Scoring multi-sites & classement portefeuille** ✅ livré PR #222
- Étendre `compute_potential_score` en classement portefeuille
- Top-10 sites à prioriser, carte de chaleur par archétype, budget flex total
- Cible DG/DAF multi-sites (Fournisseur 4.0)
- **Effort** : 5-6 j · ✅ livré PR #222 · **Impact** : Voltalis reste mono-site · **Dépend** : scope hierarchy existant
- **Livraison** : endpoint `/api/pilotage/portefeuille-scoring` + carte Cockpit `PortefeuilleScoringCard`
- **Follow-up** : Option C (PR #227) wire Site model réel · Sprint 1 UX (PR #229) CTAs + scope switcher

### Vague 2 — Q3 2026 (preuve ROI chiffré)

**4. Simulation NEBCO sur vraie CDC Enedis**
- Rejouer la CDC SF4 d'un site sur 30 derniers jours + appliquer fenêtres FAVORABLES détectées
- Estimer gain NEBCO réel (spread × kWh décalés − compensation)
- "Voici les 1 847 € que vous auriez gagnés le mois dernier"
- **Effort** : 6-7 j · **Impact** : preuve chiffrée sans engagement agrégateur · **Dépend** : CDC SF4 Enedis + spot historique

**5. Détecteur d'anomalies conso + talon gaspillé**
- ML non-supervisé (Isolation Forest) sur la CDC
- Dérives talon nocturne, pics anormaux week-end, "fantômes" post-fermeture
- Chaque anomalie → action chiffrée
- **Effort** : 5 j · **Impact** : combine flex + anomalie (Voltalis fait flex, Metron fait anomalie, personne combine) · **Dépend** : CDC historique 30j+

### Vague 3 — Q4 2026 (moat durable)

**6. Jumeau thermique léger bâtiment (RC-model)**
- Modèle R-C à 2 paramètres calé sur CDC + DJU + archétype
- Prédit effet d'un décalage chauffage/clim en °C ressenti
- Transforme "vous perdrez 0,5 °C pendant 2h" en décision gestionnaire
- **Effort** : 8-10 j · **Impact** : répond à l'objection #1 du tertiaire (confort) · **Dépend** : DJU Météo-France + CDC

**7. Leaderboard CUBE Flex interne (gamification portefeuille)**
- Challenge inspiré CUBE Flex A4MT
- Classement mensuel % baisse pointe 7h-10h + 17h-20h (28% conso tertiaire)
- Badges par site, partage inter-sites du même org
- **Effort** : 4 j · **Impact** : engagement exploitants terrain (les BACS non exploités = 45%) · **Dépend** : CDC + plages pointe constants.py

**8. Marketplace "primo-agrégateurs" intégrée**
- API de matching PROMEOS → Voltalis/NW/Équilibre
- Dossier technique pré-rempli (NEBCO-ready, CDC 12 mois, Flex Ready® score)
- Commission 10-15% = stream revenu Fournisseur 4.0
- **Effort** : 10-12 j + juridique · **Impact** : PROMEOS devient guichet unique, pas concurrent · **Dépend** : partenariats agrégateurs agréés RTE

## Synthèse

| Vague | Effort total | Impact | Angle différenciant | Statut |
|---|---|---|---|---|
| **V1 (Q2)** | 12-14 j/dev | Cockpit J+7 + ROI CFO + portefeuille | Visibilité anticipée unique | ✅ livré PR #222 · Option C PR #227 mergée · Sprint 2 dette PR #231 mergée · Sprint 1 UX PR #229 + Sprint 3 docs PR #230 en review |
| **V2 (Q3)** | 11-12 j/dev | Preuve chiffrée sur données réelles | Anti-objection "je n'y crois pas" | ⏳ à démarrer |
| **V3 (Q4)** | 22-26 j/dev | Moat durable (jumeau + gamification + marketplace) | Guichet unique flexibilité | ⏳ à démarrer |

**Total 45-52 j/dev** sur 3 trimestres pour passer de "brique Pilotage conforme" à "meilleure brique au monde".

## Dette technique identifiée par audit (S22)

Corrigée dans ce même sprint :
- ✅ Org-scoping Flex Ready endpoint
- ✅ `except Exception` silencieux → logger.warning + typage
- ✅ Fallback spot avec `prix_age_hours` + cap 36h
- ✅ `empreinte_source` lu depuis config/emission_factors.py
- ✅ Injection tz : datetime naïf = UTC (pas wall-clock)

Dettes traitées Sprint 2 (PR #231 mergée) :
- ✅ Tests DST spring-forward/fall-back sur `is_hc_favorable` — `test_pilotage_radar_dst.py` + `test_pilotage_turpe7_dst.py` (6 tests, finding documenté `<` fold=0/1 → `.timestamp()`)
- ✅ `response_model` Pydantic sur endpoint Flex Ready (OpenAPI) — fait (tous les 4 endpoints ont `response_model`)
- ✅ Tests fallback spot stale + module entsoe indisponible — déjà couvert `test_pilotage_flex_ready.py` tests 5+6 + Option C tests (+ filtre `end_date` contrat actif ajouté)
- ✅ Pondérations `_W_DECALABLE/_W_POINTE/_W_BACS` + 7 constantes ROI vers ParameterStore — `services/pilotage/parameters.py` façade + section `pilotage_flex_ready:` dans `tarifs_reglementaires.yaml` (15 entries avec `valid_from` + `source` citée)

Dettes restantes à planifier :
- ❌ Mapping NAF → archétype via `utils/naf_resolver` (supprimer heuristique hôtellerie biaisée)
- ❌ Dedup `services/pilotage/parameters.py` vs `services/billing_engine/parameter_store.py` (~200 LOC duplication identifiée par review PR #231)
- ❌ StrEnum `ActionSourceType` / `prix_source` pour type safety
- ❌ Memo local dans `compute_portefeuille_scoring` (2× N lookups YAML)
- ❌ `conftest.py` partagé pour fixtures DB pilotage
