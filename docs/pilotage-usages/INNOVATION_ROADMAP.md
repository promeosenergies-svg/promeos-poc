# Innovation Roadmap — Pilotage PROMEOS post-S22

**Objectif** : faire du module Pilotage "le meilleur au monde" en exploitant les **vraies données signal** (ENTSO-E, Tempo, Enedis CDC) pour créer des cas d'usage que ni Voltalis, ni NW, ni les GTB Flex Ready® ne font aujourd'hui.

**Socle acquis (S17-S22)** : doctrine Pilotage, fenêtres J+7, 7 quick wins, pipeline RTE Tempo OAuth2 + ENTSO-E + APScheduler, Flex Ready® NF EN IEC 62746-4, TURPE 7 HC saisonnalisés, calibrage Enedis 2024.

## 8 pistes ambitieuses par ordre de séquençage

### Vague 1 — Q2 2026 (zéro dépendance externe, impact cockpit)

**1. Radar prix négatifs J+7 (alertes proactives)**
- Modèle ML léger (gradient boosting) sur historique ENTSO-E + météo + PV installé
- Prédit les 513h/an de prix négatifs à J+7
- Cockpit : "3 fenêtres négatives probables cette semaine — déclenchez vos ECS/VE"
- **Effort** : 4-5 j/dev · **Impact** : wedge unique (agrégateurs voient H-1, nous voyons J+7) · **Dépend** : Open-Meteo gratuit

**2. ROI Flex Ready® chiffré par site**
- Au-delà du signal conforme NF EN IEC 62746-4, calcul du **gain € annuel**
- Évitement pointe + valorisation NEBCO spread + CEE BACS
- Transforme un standard coché en business case CFO
- **Effort** : 3 j · **Impact** : aucun concurrent ne chiffre · **Dépend** : grille TURPE 7 + spread NEBCO historique

**3. Scoring multi-sites & classement portefeuille**
- Étendre `compute_potential_score` en classement portefeuille
- Top-10 sites à prioriser, carte de chaleur par archétype, budget flex total
- Cible DG/DAF multi-sites (Fournisseur 4.0)
- **Effort** : 5-6 j · **Impact** : Voltalis reste mono-site · **Dépend** : scope hierarchy existant

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

| Vague | Effort total | Impact | Angle différenciant |
|---|---|---|---|
| **V1 (Q2)** | 12-14 j/dev | Cockpit J+7 + ROI CFO + portefeuille | Visibilité anticipée unique |
| **V2 (Q3)** | 11-12 j/dev | Preuve chiffrée sur données réelles | Anti-objection "je n'y crois pas" |
| **V3 (Q4)** | 22-26 j/dev | Moat durable (jumeau + gamification + marketplace) | Guichet unique flexibilité |

**Total 45-52 j/dev** sur 3 trimestres pour passer de "brique Pilotage conforme" à "meilleure brique au monde".

## Dette technique identifiée par audit (S22)

Corrigée dans ce même sprint :
- ✅ Org-scoping Flex Ready endpoint
- ✅ `except Exception` silencieux → logger.warning + typage
- ✅ Fallback spot avec `prix_age_hours` + cap 36h
- ✅ `empreinte_source` lu depuis config/emission_factors.py
- ✅ Injection tz : datetime naïf = UTC (pas wall-clock)

À traiter en V1 :
- Tests DST spring-forward/fall-back sur `is_hc_favorable`
- `response_model` Pydantic sur endpoint Flex Ready (OpenAPI)
- Tests fallback spot stale + module entsoe indisponible
- Mapping NAF → archétype via `utils/naf_resolver` (supprimer heuristique hôtellerie biaisée)
- Pondérations `_W_DECALABLE/_W_POINTE/_W_BACS` vers ParameterStore
