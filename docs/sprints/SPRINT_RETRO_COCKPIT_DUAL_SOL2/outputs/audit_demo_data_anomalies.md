# Audit cohérence données démo Cockpit (vs seed HELIOS S)

> Signalé utilisateur 2026-05-01 sur captures Cockpit Pilotage + Vue exécutive.
> Vérification runtime via FastAPI TestClient sur `/api/cockpit/_facts?org_id=1`.

## Constat global

Les données affichées NE SONT PAS truquées — elles sont calculées depuis le
seed démo HELIOS S en DB. Mais 4 effets visuels paraissent aberrants pour un
CFO/EM externe parce que (a) le seed contient des incohérences temporelles,
et (b) la couche d'affichage présente les fallbacks comme des données fraîches.

## Anomalies détectées

### Anomalie #1 — `peak_source: "j-99"` affiché comme "Mesure du J-99 (CDC J-1 en synchro SGE)"

**Runtime** :

```json
"power": {
  "peak_j_minus_1_kw": 294.5,
  "subscribed_kw": 1480.0,
  "delta_pct": -80,
  "peak_time": "16:30",
  "peak_source": "j-99"
}
```

**Diagnostic** : Le helper `_build_power` cherche le pic puissance dans les
N derniers jours (max 99). La dernière mesure trouvée date de **J-99**
(~3 mois en arrière). Le seed démo n'a pas de PowerReading J-1.

**Effet UX** : la card Pilotage affiche "Mesure du J-99 (CDC J-1 en synchro
SGE)" — l'utilisateur croit que la donnée est en cours de synchro alors
qu'elle date de 3 mois. **Trompeur**.

**Action recommandée** :

- **Court terme** (Phase 28) : afficher "Mesure ancienne — dernière donnée
  3 mois" + badge "CONNECTEUR À VÉRIFIER" si peak_source != j-1/j-2/j-3.
- **Moyen terme** : étendre le seed démo HELIOS S avec PowerReading
  quotidiennes jusqu'à J-1.

### Anomalie #2 — `j_minus_1_mwh: 25.56` vs `baseline: 8.757` → +192 %

**Runtime** :

```json
"j_minus_1_mwh": 25.56,
"j_minus_1_source": "j-2",
"baseline_j_minus_1": {
  "value_mwh": 8.757,
  "method": "a_historical",
  "delta_pct": 192
}
```

**Diagnostic** : la baseline `a_historical` (moyenne des mêmes jours sur
12 semaines glissantes) vaut 8.757 MWh, soit **3× moins** que la mesure
J-2 (25.56 MWh). Soit le seed contient des jours fortement déséquilibrés
(quelques jours seedés à 25 MWh + beaucoup à ~5 MWh), soit la baseline est
calculée sur une fenêtre trop courte (peu de jours historiques).

**Effet UX** : "+192 %" affiché en rouge alarme — le CFO croit qu'il y a
une dérive critique alors que c'est un artefact du seed.

**Action recommandée** : générer un seed démo avec une baseline historique
réaliste (4-6 mois de données quotidiennes consistantes), pas juste 12
semaines avec quelques jours pic.

### Anomalie #3 — `current_month_label: "mai 2026 (j 1-1)"` et `0 % vs mai 2025`

**Runtime** :

```json
"monthly_vs_n1": {
  "current_month_label": "mai 2026 (j 1-1)",
  "current_month_mwh": 0.0,
  "previous_year_month_normalized_mwh": 0.0,
  "delta_pct_dju_adjusted": 0,
  "confidence": "faible"
}
```

**Diagnostic** : on est le 1er mai 2026 matin → 1 jour de mai inclus, mais
**0 MWh enregistré encore** sur cette journée. La comparaison vs mai 2025
= 0/0 → delta 0 % (faux). Le champ `confidence: "faible"` est exposé mais
n'est pas mis en avant côté UI.

**Effet UX** : "0 % vs mai 2025" affiché comme données stables → trompeur
en début de mois.

**Action recommandée** :

- **Court terme** (Phase 28.1) : si `current_month_label` contient `(j 1-X)`
  avec X ≤ 3, afficher "Données en cours d'agrégation — patientez quelques
  jours" au lieu du delta.
- **Moyen terme** : utiliser le mois précédent COMPLET pour la comparaison
  vs N-1 quand on est dans les 3 premiers jours du mois courant.

### Anomalie #4 — Trajectoire 2030 chute brutale 4 229 → 2 342 dès 2026

**Runtime** :

```json
"annual_mwh": 2756.2,
"annual_mwh_dt": 4229.2,
"trajectory_2030_score": 0,
"trajectory_method": "c_regulatory_dt"
```

**Visuel** : courbe verte "projection" passe de 4 229 (2026) à 2 342 (2027)
puis plateau jusqu'à 2030. Le réel (bleu) monte au-dessus de la cible DT
(rouge).

**Diagnostic** : la projection applique l'effet **total** des actions
BACS+APER au plus proche de la première échéance (2027), au lieu d'étaler
linéairement entre date d'engagement et échéance finale. Résultat : chute
brutale au lieu de lissage.

**Effet UX** : "2 342 MWh atteint dès 2027" semble irréaliste — un audit
externe dirait "comment voulez-vous économiser 1887 MWh en 1 an ?".

**Action recommandée** (Phase 30 trajectoire) : implémenter un lissage
temporel par interpolation linéaire entre `today` et chaque
`action.due_date`, plutôt qu'un step function.

## Statut Phase 27 (mini-sprint courant)

Phase 27 livre `_facts.consumption.weekly_breakdown[]` — backend expose les
**vraies** valeurs MWh par jour des 7 derniers jours, et le SVG FE consomme
ces données au lieu de hauteurs hardcodées. Cela résout :

- Le tooltip affichera la vraie MWh par jour, pas une estimation depuis
  position SVG (Phase 26.bis hot-fix)
- L'anomalie visuelle (samedi rouge +39 %) sera dérivée du backend
  (`is_anomaly: true, delta_pct: +39`) au lieu d'être hardcodée
- Si le seed contient des trous (J-2 réel mais J-1 vide), le tooltip
  affichera explicitement "donnée manquante" au lieu de mentir

Mais **les 4 anomalies ci-dessus restent à traiter** dans des phases
ultérieures (28 = seed démo, 29 = narrative honnête fallbacks, 30 =
trajectoire lissage).

## Tickets follow-up

| Phase | Ticket | Effort | Priorité |
|---|---|---|---|
| 28 | Améliorer seed démo HELIOS S — PowerReading J-1 + baseline historique cohérente | 4-6h | P1 (avant démo Q3) |
| 29 | Narrative honnête fallback : "Mesure du J-99" → badge "CONNECTEUR À VÉRIFIER" | 2-3h | P2 |
| 29bis | Premier mois affichage : "Données en cours d'agrégation" si j ≤ 3 | 1h | P2 |
| 30 | Trajectoire 2030 — lissage temporel interpolation linéaire | 4h | P1 (avant démo) |
