# Méthodologie — Achat énergie post-ARENH

> Référence accessible depuis le SolPageFooter de `/achat-energie`.
> Dernière révision : 2026-04-27 (Sprint 1.6).

## Objet

PROMEOS Sol n'est **pas fournisseur d'énergie**. La page `/achat-energie` propose une comparaison neutre des 30+ fournisseurs CRE actifs sur le marché B2B français post-ARENH (mécanisme terminé le 31/12/2025). Le moteur shadow billing 6 composantes audite chaque offre face aux barèmes officiels en vigueur.

## Contexte marché post-ARENH

- **ARENH terminé** : 100 TWh d'électricité nucléaire à 42 €/MWh disparus du marché B2B le 31/12/2025
- **VNU (Versement Nucléaire Universel)** : remplaçant partiel ARENH, fléché TRVE résidentiel + ELD, transparence partielle pour B2B
- **Capacité 1/11/2026** : nouveau mécanisme RTE Y-1 / Y-4 — surcoût ~3-7 €/MWh selon profil
- **30+ fournisseurs CRE** : observatoire CRE T4 2025 — concentration moyenne, fenêtre négociation favorable

## 6 composantes shadow billing auditées

| # | Composante | Source officielle |
|---|-----------|-------------------|
| 1 | **TURPE 7** (acheminement réseau élec) | CRE délibération 2024-273 — grille 1/08/2025-2029 |
| 2 | **Accise élec** (CSPE + accises unifiées) | LFI 2026 — taux 26,58 €/MWh dom. / 22,50 industriel |
| 3 | **CTA** (Contribution Tarifaire d'Acheminement) | Code énergie L.121-37, taux % CSPE |
| 4 | **Capacité RTE** (Y-1 / Y-4 obligation) | RTE Règles Mécanisme Capacité, mise à jour 11/2026 |
| 5 | **ATRD7 GRDF** (gaz, le cas échéant) | CRE délibération 2026-83 — grille 1/07/2026 |
| 6 | **VNU post-ARENH** (transparence partielle) | LFI 2026 + délibération CRE 2026-25 |

## Algorithme

### 1. Estimation budget annuel exposé

Pour chaque contrat actif arrivant à échéance :

```python
volume_mwh = consommation_annuelle_estimée_mwh    # extrait conso unifiée ou défaut 250 MWh/site
prix_unitaire_actuel = contrat.price_ref_eur_per_kwh
budget_actuel_eur = volume_mwh * 1000 * prix_unitaire_actuel
```

### 2. Reconstitution offre challenger neutre

```python
prix_marche_estimé = base_marche_EPEX(profil) + TURPE7 + accises + CTA + capacité
ecart_marche_eur_par_kwh = prix_unitaire_actuel - prix_marche_estimé
```

### 3. Économie potentielle

Heuristique conservative basée sur observatoire CRE T4 2025 (médiane appels d'offres B2B post-ARENH) : **8 % du volume exposé**. La fourchette publique varie de 5 % (gros volumes déjà optimisés) à 12 % (petites ETI sans renégociation récente).

```python
economie_potentielle_eur = volume_expose_eur * 0.08
```

### 4. Stratégies comparées

| Stratégie | Profil-cible | Wedge / risque |
|----------|-------------|----------------|
| **Fixe** | DAF prudent, budget prévisible | Aucune exposition marché — sécurité prime |
| **Indexé** | ETI moyenne, tolérance modérée | Suit indice avec plafond — économie 5-10 % vs Fixe |
| **Spot** | Profil averti, energy manager | Prix temps réel — économie max, volatilité forte |
| **Tarif Heures Solaires** | Site avec process flexibles | Créneaux midi-après-midi été · 8h-10h + 17h-20h hiver · sans pénalité |

### 5. Échéances & priorisation

- `< 90 jours` → **DRIFT** (urgence préavis résiliation)
- `90 j ≤ x < 12 mois` → **TODO** (mise en concurrence à anticiper 6 mois avant)
- `> 12 mois` → information surveillée, pas d'action immédiate

## KPIs hero §5

### 1. Échéances < 12 mois
Nombre de `EnergyContract.end_date` tombant dans les 365 prochains jours pour le scope organisation/site sélectionné.

### 2. Volume exposé
`Σ (volume_mwh × prix_unitaire_actuel)` sur les contrats à échéance. Source : `EnergyContract.price_ref_eur_per_kwh` × consommation annuelle estimée (250 MWh/site défaut si conso non renseignée).

### 3. Économie potentielle
`volume_exposé × 0,08` — médiane CRE T4 2025. Calcul affiché à l'utilisateur avec précision « estimation conservative ».

## Provenance

Niveau de confiance affiché :
- **Haute** : barèmes officiels appliqués + ≥ 1 contrat avec `price_ref_eur_per_kwh` renseigné
- **Moyenne** : estimation 250 MWh/site faute de conso unifiée fine
- **Faible** : aucun contrat actif référencé — invitation à importer

## Référence interne

- `backend/services/narrative/narrative_generator.py:_build_achat_energie`
- `backend/models/billing_models.py:EnergyContract`
- `backend/config/tarifs_reglementaires.yaml` — ParameterStore versionné CRE/JORF
- `backend/services/billing_engine/catalog.py` — catalogue 6 composantes shadow

## Sources publiques consultables

- [CRE — Observatoire des marchés T4 2025](https://www.cre.fr/observatoire) — concentration / parts marché B2B
- [Légifrance — LFI 2026 art. accises](https://www.legifrance.gouv.fr/loda/id/LEGITEXT000050994196) — taux accises 2026
- [RTE — Mécanisme de capacité](https://www.services-rte.com/fr/decouvrez-nos-offres-de-services/mecanisme-de-capacite.html) — règles 2026
- [Code de l'énergie — L.336-1 ARENH](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000022493871) — fin 31/12/2025

## Différenciation marché

À notre connaissance, aucun acteur concurrent (Advizeo / Deepki / Citron / Energisme / Trinergy) ne propose en B2B la combinaison neutralité non-fournisseur + shadow billing 6 composantes + comparaison transparente 30+ offres CRE. Le wedge concurrentiel principal est la **neutralité durable** : PROMEOS ne touche aucune commission fournisseur.

## Versioning

Mises à jour barèmes (TURPE, accises, ATRD, capacité) → `tarifs_reglementaires.yaml` versionné. Modifications heuristique économie ou benchmark CRE → commit explicite + révision de cette page.
