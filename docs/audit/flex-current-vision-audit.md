# Audit Flex — Vision actuelle PROMEOS

**Date :** 2026-03-18
**Branche :** `audit/flex-current-vision`
**Statut :** Audit-only, aucun code modifié

---

## 1. DÉCISION / RÉSULTAT

**PROMEOS est structurellement prêt à accueillir une brique flexibilité.** Le socle existant (patrimoine, conformité, billing, purchase, action center) couvre 70-80% des prérequis. Les gaps sont identifiés et comblables en 3-4 sprints ciblés sans refonte.

---

## 2. AUDIT — CONSTATS

### A. Existant technique (ce qui est déjà là)

| Composant | Maturité | Fichiers clés |
|-----------|----------|---------------|
| **Flex Mini** (scoring heuristique HVAC/IRVE/Froid) | PARTIEL | `services/flex_mini.py`, `routes/flex.py` |
| **EMS Timeseries** (courbes 15min/horaire/jour) | COMPLET | `services/ems/timeseries_service.py`, `routes/ems.py` |
| **Signature énergétique** (modèle piecewise changement de pente) | COMPLET | `services/ems/signature_service.py` |
| **Détection schedule** (horaires d'ouverture multi-intervalles) | COMPLET | `services/schedule_detection_service.py` |
| **HP/HC + TOU** (grilles tarifaires versionnées) | COMPLET | `models/tou_schedule.py`, `models/tariff_calendar.py` |
| **REFLEX_SOLAR** (6 blocs demand response) | COMPLET | `services/purchase_service.py` |
| **Monitoring** (KPI, alertes, qualité données, benchmarks) | COMPLET | `services/electric_monitoring/` |
| **BACS/GTB** (assets CVC, classe EN 15232, éligibilité) | COMPLET | `models/bacs_models.py`, `services/bacs_*` |
| **APER/PV** (estimation PVGIS, conformité solarisation) | COMPLET | `services/aper_service.py` |
| **Usages** (taxonomie 12 types dont IRVE, CVC, process) | COMPLET | `models/usage.py` |
| **Baselines** (UsageBaseline avant/après) | COMPLET | `models/usage.py` |
| **Weather** (cache météo, signature thermique) | PARTIEL | `services/ems/weather_service.py` (démo uniquement) |
| **Action center** (issues, workflow, audit trail, recommandations) | COMPLET | Sprint 7-20 |

### B. Ce qui manque pour la flexibilité

| Gap | Criticité | Impact |
|-----|-----------|--------|
| **Aucun modèle asset pilotable** (batterie, stockage thermique, IRVE réel) | P0 | Impossible d'inventorier les leviers de flex par site |
| **Pas de dispatch/commande** (ordre de pilotage, consigne) | P1 | Flex reste du scoring, pas de l'opérationnel |
| **Météo réelle absente** | P1 | Signature et baseline non fiabilisés en production |
| **Pas de DJU/DJC** (degrés-jours) | P1 | Normalisation climatique incomplète |
| **IRVE non basé sur inventaire** | P2 | Scoring IRVE heuristique, pas d'asset réel |
| **PV génération non intégrée** | P2 | APER estime mais ne suit pas la production réelle |
| **Pas de multi-énergie flex** (gaz/réseau chaleur) | P2 | Focus électricité uniquement |
| **NEBCO/NEBEF non modélisé** | P1 | Valorisation flex sur marché wholesale absente |

### C. Logique produit — ruptures et continuités

| Chaîne | Continuité | Rupture |
|--------|------------|---------|
| Patrimoine → Flex | ✅ site/bâtiment/compteur/CVC existent | ❌ Pas d'objet "asset pilotable" |
| Conformité BACS → Flex | ✅ Classe GTB A/B/C/D + puissance utile | ❌ Pas de lien GTB classe → potentiel flex |
| Conso/EMS → Flex | ✅ Courbes, signature, schedule, HP/HC | ✅ Bon socle (flex_mini utilise déjà) |
| Billing → Flex | ✅ Contrats, TURPE, shadow billing | ❌ TURPE 7 / heures solaires non intégrés |
| Purchase → Flex | ✅ REFLEX_SOLAR 6 blocs | ❌ Pas de lien avec NEBCO |
| Actions → Flex | ✅ Action center complet | ✅ Recommandations prescriptives en place |

---

## 3. AUDIT RÉGLEMENTAIRE — Mars 2026

| Réglementation | Statut | Échéance clé | Impact PROMEOS |
|----------------|--------|-------------|----------------|
| **NEBCO** (ex-NEBEF) | En vigueur 1/09/2025 | Actif | Flex bidirectionnelle, nouvelles méthodes de mesure |
| **TURPE 7** | En vigueur 1/08/2025 | MAJ annuelles 08/2026-28 | Nouveau spread HP/HC, tarif stockage 08/2026 |
| **Réforme HC solaires** | Phase 1 active 11/2025 | Phase 2 : 12/2026-10/2027 | HC midi (11h-17h), refonte complète tarifs |
| **Mécanisme capacité** | Transition | Nouveau méca hiver 2026-27 | Enchères centralisées DP-4 |
| **AOFD** (RTE) | Actif | Appels annuels | 28 863 €/MW + bonus |
| **BACS >290kW** | En vigueur | 01/01/2025 (passé) | Conformité active |
| **BACS 70-290kW** | Reporté | 01/01/2030 | Pipeline commercial large |
| **APER parking >10 000 m²** | En vigueur | **01/07/2026** (imminent) | Auto-conso solaire obligatoire |
| **APER parking 1 500-10 000 m²** | En vigueur | 01/07/2028 | Idem |
| **CEE P6** | En vigueur 01/01/2026 | 2026-2030 | Financement projets GTB/flex |

**Points à forte variabilité :** seuil NEBCO (100 kW ?), calendrier phase 2 HC, modalités AOFD 2026.

---

## 4. PLAN P0 / P1 / P2

### P0 — Fondations flex (Sprint 21-22)
1. **FlexAsset model** : inventaire assets pilotables (HVAC, IRVE, stockage, PV)
2. **Lien BACS → Flex** : classe GTB + puissance → potentiel flex
3. **TURPE 7 grille** : intégrer les nouveaux barèmes + heures solaires
4. **NEBCO signal model** : structure pour valorisation flex marché

### P1 — Opérationnel (Sprint 23-24)
5. **FlexBaseline** : baseline défendable par asset (signature + schedule + weather)
6. **FlexPotential calculé** : potentiel kW/kWh par levier par site
7. **Météo réelle** : connecteur Open-Meteo ou Météo-France
8. **DJU/DJC** : normalisation climatique sur signature

### P2 — Pilotage (Sprint 25-26)
9. **PilotageOrder** : commande de flex (consigne, durée, asset, validation)
10. **FlexPortfolio** : vue portefeuille multi-sites flex
11. **IRVE inventaire** : modèle borne de recharge + profil de charge
12. **PV production tracking** : suivi génération réelle vs estimée

---

## 5. IMPLÉMENTATION RECOMMANDÉE

### Nouveaux modèles
```
FlexAsset (site_id, type, power_kw, energy_kwh, controllable, bacs_asset_id)
FlexBaseline (asset_id, method, period, baseline_kwh, confidence)
FlexPotential (site_id, lever, potential_kw, potential_kwh_year, confidence, source)
PilotageOrder (asset_id, order_type, start, end, target_kw, status, actor)
NebcoSignal (date, bloc, direction, price_eur_mwh, source)
```

### Nouveaux endpoints
```
GET  /api/flex/assets?site_id=
POST /api/flex/assets
GET  /api/flex/potential?site_id=
GET  /api/flex/portfolio
GET  /api/flex/nebco/signals
POST /api/flex/pilotage/orders
```

### Fichiers existants à enrichir
- `services/flex_mini.py` → utiliser FlexAsset au lieu de heuristics
- `services/purchase_service.py` → intégrer NEBCO + TURPE 7
- `models/tou_schedule.py` → ajouter heures solaires
- `routes/ems.py` → exposer baseline défendable

---

## 6. TESTS & QA

### Tests à ajouter
1. FlexAsset CRUD + lien BACS
2. FlexPotential calculé = cohérent avec flex_mini existant
3. Baseline défendable + confidence
4. TURPE 7 grille correcte
5. Heures solaires HC = 11h-17h
6. NEBCO signal structure
7. Invariant : flex_potential cohérent patrimoine/conformité/billing

### Definition of Done
- [ ] FlexAsset modèle + migration
- [ ] Lien BACS classe → potentiel flex
- [ ] TURPE 7 grilles intégrées
- [ ] Heures solaires dans TOU
- [ ] 5+ tests flex invariants
- [ ] Aucune régression sur la chaîne PROMEOS

---

## 7. TOP 10 ANGLES MORTS

1. Flex scoring sans asset réel = non défendable en audit
2. Météo démo = baseline non fiabilisé
3. TURPE 7 non intégré = calculs facture obsolètes
4. Heures solaires non intégrées = HP/HC faux
5. NEBCO absent = valorisation marché impossible
6. PV production non suivie = APER incomplet
7. IRVE heuristique = pas d'inventaire borne
8. Pas de DJU/DJC = normalisation absente
9. Pas de dispatch/commande = flex théorique
10. Multi-énergie absent = électricité only

## 8. TOP 10 QUICK WINS

1. Créer FlexAsset (modèle + CRUD) — effort S
2. Lier BacsCvcSystem → FlexAsset — effort S
3. Ajouter heures solaires dans TOU (11h-17h HC) — effort S
4. Intégrer grille TURPE 7 dans tariff_calendar — effort M
5. Connecter Open-Meteo (gratuit, sans clé) — effort S
6. Calculer DJU/DJC depuis weather cache — effort S
7. Exposer flex_potential enrichi dans patrimoine — effort S
8. Créer NebcoSignal structure — effort S
9. Ajouter "Flexibilité" dans la navigation — effort S
10. Relier recommandations → levier flex — effort M

## 9. SÉQUENCEMENT 3 PROCHAINS SPRINTS

### Sprint 21 : Fondations Flex
- FlexAsset model + CRUD + lien BACS
- TURPE 7 grille + heures solaires
- Tests fondations

### Sprint 22 : Données & Baseline
- Connecteur Open-Meteo réel
- DJU/DJC
- FlexBaseline calculé
- FlexPotential enrichi (ex-flex_mini)

### Sprint 23 : Valorisation & Portfolio
- NEBCO signal model
- FlexPortfolio multi-sites
- Lien purchase → flex → NEBCO
- Vue UI flex dans patrimoine/conformité

## 10. RISQUES DE RÉGRESSION SI ON CODE TROP VITE

1. Casser le scoring conformité en ajoutant flex sans garde-fou
2. Désynchroniser billing/purchase si TURPE 7 mal intégré
3. Invalider les tests HP/HC si heures solaires mal branchées
4. Créer un doublon flex_mini vs FlexPotential
5. Introduire des KPI flex non traçables (formule/source manquante)
