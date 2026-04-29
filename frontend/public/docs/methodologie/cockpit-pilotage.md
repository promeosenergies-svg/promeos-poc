# Méthodologie — Cockpit Pilotage (Briefing du jour)

> Référence accessible depuis le footer de `/cockpit/jour`.
> Dernière révision : 2026-04-29 (Sprint Refonte WOW Cockpit dual sol2).

## Objet

Le **Briefing du jour** est la page d'arbitrage opérationnel pour l'energy manager — lecture en **30 secondes**, doctrine §11.3. Elle expose les signaux directement actionnables (anomalies de consommation J−1, dérive de facture mensuelle vs N−1 normalisé, dépassement contractuel pic puissance) + une file de traitement priorisée par impact.

Source unique partagée avec la Synthèse stratégique (`/cockpit/strategique`) via l'endpoint atomique `/api/cockpit/_facts`. Aucune logique métier frontend (doctrine §8.1).

## Triptyque KPI temporel multi-échelle

L'ordre du triptyque suit la logique cognitive « vue météo → alerte vive → signal contractuel » :

### 1. MOYEN TERME — Conso mois courant
- **Source** : `/api/cockpit/_facts.consumption.monthly_vs_n1`
- **Méthode** : conso mois courant (j 1–jour J) vs même fenêtre N−1, normalisée DJU (Degré Jour Unifié, méthode COSTIC).
- **Baseline** : `b_dju_adjusted` calibrée glissante 12 mois — si moins de 90 j de data, fallback sur `a_historical`.
- **Confiance** : haute si r² ≥ 0,7 — sinon faible.
- **Tooltip canonique** : "avril 2026 (j 1-29) vs N−1 normalisé · Baseline B DJU-ajustée · r² 0,87 · calibrée 20/04/2026".

### 2. COURT TERME — Conso J−1
- **Source** : `/api/cockpit/_facts.consumption.j_minus_1_mwh + .baseline_j_minus_1`
- **Méthode** : moyenne 12 mêmes jours de la semaine sur 12 semaines glissantes (`a_historical`).
- **Fallback intelligent** : si J−1 = 0 (lundi sans seed dimanche, trou EMS), boucle J−2 → J−7 jusqu'à data > 0. Le hint mono indique `Mesure du J−N · J−1 en synchro EMS`.
- **Sous-compteurs filtrés** : agrégation portfolio sur compteurs principaux uniquement (`parent_meter_id IS NULL`). Les sous-compteurs CVC / éclairage / IT sont réservés au drill-down par usage.

### 3. CONTRACTUEL — Pic puissance J−1
- **Source** : `/api/cockpit/_facts.power.peak_j_minus_1_kw + .subscribed_kw`
- **Méthode** : `MAX(P_active_kw)` sur la courbe de charge 30 min (CDC) du jour J−1, comparé à la puissance souscrite contractuelle (kVA agrégée).
- **Fallback élargi** : 30 j (CDC seedé mensuellement) puis dernier point disponible.

## File de traitement P1-P5

5 priorités classées par urgence × domaine, alimentées par 3 sources :

1. **Action center issues** critiques/high (conformité)
2. **ActionPlanItem overdue** (open + due_date < now)
3. **Risque financier > 5 000 €** (= `_facts.exposure.total.value_eur`, source `_build_exposure` doctrine §11.3 single SoT)

Chaque ligne expose `category_label` (Anomalie / Dépassement / Hors horaires / Conformité op / Exposition) discriminant visuel + impact chiffré (€ ou MWh/an).

## Réciprocité Pilotage ↔ Décision (DoD 5)

Les 3 premières lignes de la file portent un lien italique **"voir impact stratégique →"** vers `/cockpit/strategique`. Symétriquement, chaque card décision Vue Exécutive porte un lien **"Voir preuve opérationnelle →"** vers `/cockpit/jour#decision-{rank}` (ancres `id="decision-X"` rendues sur chaque ligne de la file).

## Anti-patterns évités (doctrine §6.3)

- Pas de KPI 4ᵉ visible (triptyque inviolable)
- Pas d'acronyme brut en titre (BACS / TURPE / ARENH glossarisés inline via `<AcronymTooltip>`)
- Pas de chiffre € sans badge confiance
- Pas de `?` muet — tooltip natif sur le label entier (underline pointillée discrète)

## Confiance & traçabilité

Footer Sol affiche systématiquement : `Source · confiance · MAJ relative · méthodologie`. Cliquer "méthodologie" mène à ce document.

## Évolutions prévues (post-sprint)

- V2 push événementiel hebdo "+X vs S-1" sur les 3 KPI hero (`weekly_deltas` exposé backend mais non encore consommé en hero).
- Étape 8 backend : enrichir `priorities[1..4].impact_value_eur` (actuellement seul P5 chiffré).
- Étape 8 backend : `weekly_anomaly` payload pour le sous-titre narratif chiffré nommé du visuel Conso 7 jours ("Sam 25 avril : +39% vs baseline — anomalie Hôtel Nice").
