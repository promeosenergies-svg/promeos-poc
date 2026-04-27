# Méthodologie — Shadow Billing v4.2 (Bill Intelligence)

> Référence accessible depuis le SolPageFooter de `/bill-intel`.
> Dernière révision : 2026-04-27 (Sprint 1.5).

## Objet

Le **shadow billing v4.2** est le moteur d'audit factures de PROMEOS Sol. Il recalcule chaque ligne de facture énergie selon les barèmes officiels en vigueur (CRE, JORF, Légifrance) et détecte les écarts. Les anomalies détectées ouvrent droit à contestation auprès du fournisseur.

## 17 mécanismes audités

### Électricité
- **TURPE 7** (CSPE / acheminement réseau) — composantes HPH / HCH / HPE / HCE par tarif soutiré
- **TURPE 6 → 7** transition reprog HC depuis août 2025
- **Accise élec T1 + T2 + T3** (CSPE → CTA + accise unifiée)
- **Capacité** (mécanisme RTE Y-4 / Y-1)
- **CSPE** (contribution au service public d'électricité, via accise)
- **TVA** (5,5 % abonnement + 20 % consommation)
- **CEE** (certificats d'économies d'énergie — passe-through)
- **VNU** (versement nucléaire universel, post-ARENH 2026)

### Gaz
- **ATRD T1 / T2 / T3 / T4 / TP** — accès tarif réseau distribution gaz
- **CTA gaz additive** (contribution acheminement, depuis 2024)
- **Accise gaz / TICGN** (constante doctrine §8.3 : 10,73 €/MWh fév 2026)
- **TDN** (tarif déterminé national, gaz biomé)
- **TVA gaz**

## Sources réglementaires citées

- [JORFTEXT000053407616](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053407616) — Arrêté 27/01/2026 accises 2026
- [CRE délibération TURPE 7](https://www.cre.fr/electricite/tarifs/turpe-7) — grille acheminement 2025-2029
- [CRE délibération 2026-83 ATRD7 GRDF](https://www.cre.fr/gaz-naturel/tarifs/atrd7) — grille gaz 1/07/2026
- [Code des impositions sur les biens et services](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000045176626/) — accises CIBS

## Algorithme

### 1. Reconstitution de facture

Pour chaque ligne facturée :

```
ligne_attendue = base_unitaire × quantité × tarif_officiel(date_consommation)
ecart = ligne_facturée - ligne_attendue
```

- `ecart > 0` (surfacturation) → BillingInsight de type `overcharge`
- `ecart < 0` (sous-facturation, rare) → BillingInsight `undercharge` (pas contestable mais signalé)

### 2. Classification anomalies

| Type | Description |
|---|---|
| `overcharge` | Surfacturation détectée (ligne facturée > recalculée) |
| `price_drift` | Dérive de prix vs dernière facture — alerte changement non communiqué |
| `shadow_gap` | Ligne facturée que le moteur ne sait pas reconstituer (taxe inconnue) |
| `duplicate` | Période ou poste facturés en double |
| `missing_period` | Trou dans la chronologie (mois manquant) |

### 3. Sévérité

| Sévérité | Critère |
|---|---|
| `low` | Perte < 50 € OU période > 24 mois |
| `medium` | 50 € ≤ perte < 500 € |
| `high` | 500 € ≤ perte < 5 000 € |
| `critical` | Perte ≥ 5 000 € OU pattern récurrent identifié |

### 4. Workflow contestation

```
OPEN  →  ACK  →  RESOLVED  ou  FALSE_POSITIVE
```

- `OPEN` : anomalie détectée, à traiter
- `ACK` : contestation formalisée et envoyée au fournisseur
- `RESOLVED` : récupération validée (avoir reçu, reclaim YTD)
- `FALSE_POSITIVE` : anomalie marquée non-pertinente (à documenter)

## KPIs hero §5

### 1. Anomalies à traiter
Nombre de `BillingInsight.insight_status == OPEN`.

### 2. Pertes à récupérer
`Σ estimated_loss_eur` sur les insights OPEN. Source : reconstitution shadow par ligne.

### 3. Récupérations YTD
`Σ estimated_loss_eur` sur les insights RESOLVED depuis le début de l'année calendaire.

## Provenance

Niveau de confiance affiché :
- **Haute** : barèmes officiels appliqués + couverture EMS ≥ 50 % du périmètre
- **Moyenne** : barèmes officiels mais couverture EMS partielle
- **Faible** : extrapolation modélisée (rare, signalé explicitement par anomalie)

## Référence interne

- `backend/services/billing_engine/` — moteur shadow v4.2
- `backend/services/billing_engine/catalog.py` — catalogue tarifs (TURPE 7, accises, TICGN, CTA)
- `backend/config/tarifs_reglementaires.yaml` — ParameterStore versionné CRE/JORF
- `backend/models/billing_models.py` — BillingInsight + InsightStatus + EnergyInvoice
- `backend/services/narrative/narrative_generator.py:_build_bill_intel`

## Différenciation marché

À ce jour les 5 acteurs concurrents recensés (Advizeo, Deepki, Citron, Energisme, Trinergy) ne couvrent pas l'audit shadow billing chiffré ligne par ligne avec contestation suivie en workflow. Cette feature est unique dans le marché B2B français.

## Versioning

Mise à jour des tarifs (CRE, JORF, accises) → publication via `tarifs_reglementaires.yaml` versionné. Modifications du moteur shadow donnent lieu à un commit explicite + révision de cette page.
