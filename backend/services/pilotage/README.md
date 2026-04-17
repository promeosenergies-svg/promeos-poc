# backend/services/pilotage/ — Onboarding développeur

Module **Pilotage des usages** de PROMEOS : détection, scoring, valorisation
et exposition des signaux de flexibilité tertiaire. Remplace l'ancien
vocabulaire "flex / effacement" par une doctrine unique (voir §5).

## Pointeurs

| Document | Chemin |
|---|---|
| Roadmap produit (8 pistes Vagues 1-3) | [`docs/pilotage-usages/INNOVATION_ROADMAP.md`](../../../docs/pilotage-usages/INNOVATION_ROADMAP.md) |
| Glossaire doctrine wording | [`docs/pilotage-usages/GLOSSAIRE.md`](../../../docs/pilotage-usages/GLOSSAIRE.md) |
| Doctrine primaire (source calibrage) | [`docs/reglementaire/barometre_flex_2026.md`](../../../docs/reglementaire/barometre_flex_2026.md) |
| YAML paramètres versionnés | [`backend/config/tarifs_reglementaires.yaml`](../../config/tarifs_reglementaires.yaml) section `pilotage_flex_ready:` |
| Norme technique Flex Ready® | NF EN IEC 62746-4 (GIMELEC / Think Smartgrids) |

> Les notes projet `memory/project_pilotage_*.md` sont conservées dans la mémoire locale du développeur PROMEOS (hors repo). Les informations promues utiles sont ingérées ici ou dans `docs/pilotage-usages/`.

## 1. Architecture — comment les sous-modules s'emboîtent

```
                       ┌──────────────────────────────────────┐
                       │  backend/routes/pilotage.py          │
                       │  (4 endpoints — §3)                  │
                       └───────────────┬──────────────────────┘
                                       │ consomme
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────────┐       ┌──────────────────────┐       ┌────────────────────┐
│ flex_ready.py     │       │ radar_prix_negatifs  │       │ portefeuille_      │
│  (5 signaux       │       │  (heuristique J+7,   │       │  scoring.py        │
│   NF EN IEC       │       │   fenêtre glissante  │       │  (top-10 + heatmap │
│   62746-4)        │       │   90 j)              │       │   archétype)       │
└────────┬──────────┘       └──────────┬───────────┘       └────────┬───────────┘
         │                              │                            │
         │                              │                            │
         ▼                              ▼                            ▼
┌────────────────────┐       ┌──────────────────────┐       ┌────────────────────┐
│ connectors/        │       │ roi_flex_ready.py    │       │ score_potential.py │
│  entsoe_day_ahead  │       │  (3 composantes :    │       │  (score 0-100      │
│  tempo (OAuth2)    │       │   pointe + NEBCO +   │       │   mono-site, S22)  │
│  ademe factors     │       │   CEE BAT-TH-116)    │       │                    │
└────────────────────┘       └──────────┬───────────┘       └────────┬───────────┘
                                        │                            │
                                        └────────────┬───────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────┐
                              │  constants.py  (calibration pure)    │
                              │                                      │
                              │  - ARCHETYPE_RULES                   │
                              │  - ARCHETYPE_CALIBRATION_2024        │
                              │  - HC_TURPE7_FAVORABLE / _EXCLURE    │
                              │  - SAISON_BASSE_MOIS                 │
                              │  Source : Baromètre Flex 2026        │
                              └──────────────────────────────────────┘
```

**Règles de dépendance** :

- `constants.py` ne dépend de rien (données pures, pas de side-effects).
- `score_potential`, `window_detector`, `usage_detector`, `roi_flex_ready`,
  `portefeuille_scoring`, `radar_prix_negatifs` lisent `constants.py`.
- `flex_ready` et `radar_prix_negatifs` consomment `connectors/entsoe_day_ahead`
  (prix spot FR day-ahead) avec fallback gracieux si indisponible.
- `routes/pilotage.py` orchestre, ne contient aucune logique métier.
- `__init__.py` reste vide d'imports pour éviter les cycles (compliance/scoring
  consomme plusieurs services de ce package).

## 2. Signaux Flex Ready® (rappel norme NF EN IEC 62746-4)

Les 5 données obligatoires standardisées (GIMELEC, Baromètre Flex 2026) :

1. **Horloge bidirectionnelle** — pas 15 min minimum
2. **Puissance max instantanée** (kW)
3. **Prix unitaire** (EUR/kWh) — spot day-ahead si frais (< 36 h), sinon tarif
4. **Puissance souscrite** (kVA)
5. **Empreinte carbone** (kgCO₂e/kWh) — source unique `config/emission_factors.py`

Le drapeau `conformite_flex_ready` est **calculé** (présence des 6 champs non-
None mappés à `_FLEX_READY_FIELD_MAP`), pas auto-proclamé.

## 3. Les 4 endpoints

| Méthode + chemin | Service appelé | Payload principal | Source doctrine | Scope auth |
|---|---|---|---|---|
| `GET /api/pilotage/flex-ready-signals/{site_id}` | `flex_ready.build_flex_ready_signals` | 5 signaux + `prix_source` + `prix_age_hours` + `conformite_flex_ready` | NF EN IEC 62746-4 + ADEME V23.6 | `site_id` numérique (Site.id réel, scope org via `_scoped_site_query`) OU clé `DEMO_SITES`. 404 si introuvable / hors scope. |
| `GET /api/pilotage/roi-flex-ready/{site_id}` | `roi_flex_ready.compute_roi_flex_ready` | `gain_annuel_total_eur` + 3 composantes + `hypotheses.parametres_sources` (trace ParameterStore) | Baromètre Flex 2026 + CEE BAT-TH-116 + CRE T4 2025 | `site_id` numérique ou clé `DEMO_SITES`. 404 si introuvable / hors scope. |
| `GET /api/pilotage/radar-prix-negatifs?horizon_days=7` | `radar_prix_negatifs.predict_negative_windows` | Liste `fenetres_predites` (ISO 8601 Europe/Paris, probabilité, prix médian, usages conseillés) | Historique ENTSO-E day-ahead FR 90 j | Auth optionnelle. Fallback `[]` si < 30 j d'historique. |
| `GET /api/pilotage/portefeuille-scoring` | `portefeuille_scoring.compute_portefeuille_scoring` | `nb_sites_total` + `gain_annuel_portefeuille_eur` + `top_10` + `heatmap_archetype` | Baromètre Flex 2026 (calibrage Enedis 2024) | Org-scopé (`auth.org_id`). Fallback `DEMO_SITES` si `PROMEOS_DEMO_MODE=true` ou auth absente. Defense-in-depth via join `Portefeuille → EntiteJuridique.organisation_id`. |

Pour le contrat exact (champs, validations Pydantic), se référer aux
docstrings de `backend/routes/pilotage.py` et aux modèles `FlexReadySignals
Response`, `RoiFlexReadyResponse`, `RadarPrixNegatifsResponse`,
`PortefeuilleScoringResponse`.

## 4. Sprints et PRs livrés

| Sprint | Livraison | PR | État |
|---|---|---|---|
| S17-S21 | Doctrine Pilotage + pipeline ENTSO-E / Tempo OAuth2 / APScheduler, fenêtres J+7, 7 quick wins | #216 | ✅ mergée |
| S22 | Flex Ready® NF EN IEC 62746-4 + TURPE 7 HC saisonnalisés + calibrage Baromètre Flex 2026 | #218 | ✅ mergée |
| V1 Vague 1 | Radar prix négatifs J+7 + ROI Flex Ready® + Portefeuille scoring (3 endpoints) | #222 | ✅ mergée |
| Option C | Wiring modèle `Site` (`archetype_code`, `puissance_pilotable_kw`, `surface_m2`) + defense-in-depth org-scope | #227 | ✅ mergée |
| Sprint 2 | Harmonisation `/flex-ready-signals/{Site.id}` + tests DST spring/fall-back + migration 7 constantes vers ParameterStore versionné | #231 | ✅ mergée |
| Sprint 1 P0 UX | CTAs cockpit + scope auth durci + wording doctrine "pilotage des usages" + humanisation archétypes | #229 | en review |
| Sprint 3 docs | README module + GLOSSAIRE + INNOVATION_ROADMAP à jour | #230 | en review (ce PR) |

## 5. Doctrine wording

Source : `docs/pilotage-usages/GLOSSAIRE.md` (doctrine canonique UX + back).

| Préféré (canonique) | À éviter | Raison |
|---|---|---|
| **Pilotage des usages** | "flex", "flexibilité", "effacement" | Le module pilote des usages (ECS, VE, pré-charge froid, clim), pas un actif de marché. "Effacement" a un sens réglementaire précis (NEBEF / MA) réservé au back. |
| **Fenêtre favorable probable** | "fenêtre prix négatif" | Côté client on ne parle pas de prix négatifs (charge cognitive + confusion juridique). |
| **Potentiel pilotable** | "potentiel flex", "potentiel d'effacement" | Aligne le scoring mono-site (0-100) sur le wording cockpit. |
| **Gain annuel estimé** (confiance "indicative") | "ROI garanti", "économies" | Honnêteté hypothèses MVP (exposées dans `payload.hypotheses`). |
| **Flex Ready®** (marque GIMELEC) | — | Usage strictement réservé à la conformité NF EN IEC 62746-4. Jamais synonyme de "flex générique". |

## 6. Tester en local

Backend port **8001** (jamais 8000 / 8080) — cf. mémoire projet.

```bash
# 1. Démarrer la stack (depuis la racine du monorepo)
npm run dev:full                      # backend 8001 + frontend 5173

# 2. Seed démo (pack helios, 3 sites Flex Ready®)
cd backend
python -m services.demo_seed --pack helios --size S --reset

# 3. Appeler les 4 endpoints (DEMO_MODE=true dans .env)
curl http://localhost:8001/api/pilotage/flex-ready-signals/retail-001
curl http://localhost:8001/api/pilotage/roi-flex-ready/bureau-001
curl "http://localhost:8001/api/pilotage/radar-prix-negatifs?horizon_days=7"
curl http://localhost:8001/api/pilotage/portefeuille-scoring

# 4. Tests backend ciblés
cd backend
python -m pytest tests/test_pilotage_*.py -v

# 5. Front — Cockpit d'entrée (trois cartes V1 Vague 1)
#    http://localhost:5173/cockpit
```

Les 3 sites démo disponibles : `retail-001` (hypermarché Montreuil),
`bureau-001` (bureau Haussmann), `entrepot-001` (entrepôt Rungis).

## 7. Backlog Vagues 2-3 (INNOVATION_ROADMAP)

| Piste | Vague | Effort | Statut |
|---|---|---|---|
| 4. Simulation NEBCO sur vraie CDC Enedis SF4 | V2 Q3 2026 | 6-7 j/dev | ❌ non démarré |
| 5. Détecteur d'anomalies conso + talon gaspillé (Isolation Forest) | V2 Q3 2026 | 5 j/dev | ❌ non démarré |
| 6. Jumeau thermique léger (modèle R-C 2 paramètres, DJU) | V3 Q4 2026 | 8-10 j/dev | ❌ non démarré |
| 7. Leaderboard CUBE Flex interne (gamification inter-sites) | V3 Q4 2026 | 4 j/dev | ❌ non démarré |
| 8. Marketplace primo-agrégateurs (API matching PROMEOS → Voltalis/NW) | V3 Q4 2026 | 10-12 j + juridique | ❌ non démarré |

Total restant : 33-38 j/dev sur 2 trimestres.

## 8. Dette technique

Dettes explicites identifiées en audit S22 (cf. INNOVATION_ROADMAP §"Dette
technique identifiée") — à traiter avant marketplace V3 :

- **Tests DST** — couverture spring-forward et fall-back sur
  `is_hc_favorable` (window_detector) et les bornes horaires de
  `HC_TURPE7_FAVORABLE / _EXCLURE`. La convention actuelle `datetime` naïf
  interprété comme UTC est safe, mais non testée sur les 2 dates critiques.
- **Mapping NAF → archétype via `utils/naf_resolver`** — actuellement
  l'heuristique hôtellerie (et autres) est en partie hardcodée dans
  `usage_detector` / `ARCHETYPE_RULES`. À migrer vers le resolver NAF canonique
  (732 codes, 15 archétypes) pour supprimer le biais hôtellerie identifié.
- **ParameterStore pour les pondérations scoring** — les constantes
  `_W_DECALABLE / _W_POINTE / _W_BACS` de `score_potential.py` sont hardcodées.
  À versionner dans le ParameterStore (même mécanique que billing V112 / V113)
  pour permettre recalibrage sans redeploy.
- **Tests fallback spot stale** — `flex_ready._get_latest_spot` cap à 36 h et
  log un `warning`, mais les deux branches (ImportError module indisponible +
  spot > 36 h) ne sont pas couvertes par les tests. À ajouter avant la bascule
  prod multi-org.
