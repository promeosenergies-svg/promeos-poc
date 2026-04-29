# Méthodologie — Synthèse stratégique (Vue Décision)

> Référence accessible depuis le footer de `/cockpit/strategique`.
> Dernière révision : 2026-04-29 (Sprint Refonte WOW Cockpit dual sol2).

## Objet

La **Synthèse stratégique** est la page d'arbitrage CODIR pour DG / CFO / Propriétaire. Audience : dirigeant non-sachant énergie, lecture en **3 minutes**, doctrine §11.3. Elle expose la trajectoire, l'exposition financière calculée loi à la main et 3 décisions à arbitrer cette semaine.

Source unique partagée avec le Briefing du jour (`/cockpit/jour`) via l'endpoint atomique `/api/cockpit/_facts`. Aucune logique métier frontend (doctrine §8.1).

## Triptyque KPI hybride avec badges Calculé / Modélisé

Doctrine §0.D décision A : tout € exposé doit être **traçable** (article réglementaire ou contrat) ou converti en MWh/an. Les 3 KPI hero portent un badge de confiance visible et un drill-down preuve.

### 1. Trajectoire 2030 (Calculé)
- **Source** : `RegOps · Décret 2019-771`
- **Score** pondéré DT 45 % / BACS 30 % / APER 25 % (poids `REGOPS_WEIGHTS_DEFAULT` doctrine).
- **Drill-down** : `/conformite?scope=org&filter=non_conform` → ouvre la liste des sites non-conformes filtrée.

### 2. Exposition pénalités (Calculé)
- **Source** : `Décret 2019-771 art. 9` + `Décret 2020-887` + `Circulaire DGEC 2024`
- **Méthode** : cumul `n × DT_PENALTY_EUR` (7 500 €/site NC) + `n × DT_PENALTY_AT_RISK_EUR` (3 750 €/site à risque) + `n × BACS_PENALTY_EUR` (1 500 €/site NC) + `n × OPERAT_PENALTY_EUR` (1 500 €/déclaration manquante). **SoT canonique** `_build_exposure` (file P5 priorities + tooltip exposition Décision affichent la même valeur).
- **Drill-down** : `/conformite?scope=org&view=exposure_components` → ouvre l'onglet Plan d'exécution avec décomposition article par article.

### 3. Potentiel récupérable (Modélisé)
- **Source** : `CEE BAT-TH-116` + `Code Énergie L233-1`
- **Méthode** : modélisé sur le référentiel Certificat d'Économie d'Énergie. Confiance "modélisée" — non engageante contractuellement.
- **Drill-down** : `/anomalies?status=open&sort=mwh_desc` → liste des actions ouvertes triées par impact MWh/an décroissant.

## Push hebdo "+X vs S−1"

La narrative stratégique 4 lignes intègre un push événementiel : `expDelta.value_eur` exposé par `_facts.exposure.delta_vs_last_week` permet d'afficher "...calculée loi à la main, en hausse de **+3,8 k€** vs semaine précédente". L'œil CFO capte la dynamique en plus de l'instantané.

## 3 décisions à arbitrer (Top 3 narrées)

Backend `/api/cockpit/decisions/top3` retourne 3 leviers **distincts** (dédup site×levier — bacs / audit_sme / achat / aper / operat). Pour chaque levier connu, le titre est transformé en **question décisionnelle** (effet conseiller) :

- BACS → "Faut-il installer un système de pilotage CVC obligatoire (Décret BACS) ?"
- Audit SMÉ → "Quel prestataire retenir pour l'audit énergétique obligatoire ?"
- Achat → "Quelle stratégie de renouvellement post-ARENH retenir ?"
- APER → "Faut-il engager le solaire parking obligatoire (loi APER) ?"
- OPERAT → "Faut-il finaliser la déclaration OPERAT annuelle ?"

Chaque card expose 8 colonnes de data si dispo : Volume / Économies modélisées (+ €/an conversion) / Pénalité légale / Référentiel / Échéance J−N / **CapEx engagé / Payback / CO₂ évité / Méthode** (badge "Estimation" pour transparence).

### Heuristique CapEx + Savings (méthode "Estimation")

Sources canoniques `doctrine/constants.py` :
- `PRICE_ELEC_ETI_2026_EUR_PER_MWH = 130 €/MWh` (médiane CRE T4 2025 post-ARENH)
- `CO2_FACTOR_ELEC_KGCO2_PER_KWH = 0.052` (ADEME Base Empreinte V23.6)

Heuristique CapEx par levier :
- BACS classe A/B : 1 200 €/MWh éco (CEE BAT-TH-116 médiane)
- Audit SMÉ : 80 €/MWh éco (Référentiel ADEME)
- Renouvellement contrat : 0 € (sans engagement CapEx)
- APER (solaire parking) : 1 500 €/MWh éco

Savings €/an = `gain_mwh × 130 €/MWh`. Payback = `CapEx / Savings × 12` mois.

## Trajectoire 2030 SVG lissée

`/api/cockpit/trajectory` expose 4 séries : `reel_mwh` (bleu) / `objectif_mwh` (rouge dashed Décret Tertiaire −40%/2030) / `projection_mwh` (vert, lissée par `action.due_date` selon Phase 1.6) / jalons 2030/2040/2050. Ligne "aujourd'hui" verticale + axes Y dynamique.

## Facture portefeuille `+22,5 % vs 2024`

`/api/purchase/cost-simulation/portfolio/{org_id}` agrège la facture annuelle prévisionnelle 2026 sur tous les sites de l'org en 6 composantes :
- **Fourniture** énergie (forward baseload × CDC annuel)
- **TURPE 7** (acheminement réseau)
- **Taxes** (accise + CTA + TVA agrégées)
- **Mécanisme capacité RTE** (PL-4/PL-1 centralisé depuis 11/2026)

Composantes inactives `<details>` collapsées (VNU dormant 2027 + CBAM hors périmètre tertiaire).

Delta vs 2024 : ratio `POST_ARENH_RATIO_2026_VS_2024 = 1.225` (médiane CRE T4 2025 ETI tertiaire post-ARENH) → `previous_year_implicit = total_2026 / 1.225`. Affiché en orange sous le total.

## Teaser Flex Intelligence

`_facts.flex_potential` : si `FlexAssessment` seedé → `mwh_year × PRICE_FLEX_NEBCO_EUR_PER_MWH` (80 €/MWh blend NEBCO+AOFD CRE T4 2025). Sinon fallback heuristique `site_count × FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR` (4 200 €/site/an médiane sites NEBCO 100 kW pilotable). Badge "Indicatif" si méthode heuristique.

## Réciprocité Décision ↔ Pilotage (DoD 5)

Chaque card décision porte un lien **"Voir preuve opérationnelle →"** vers `/cockpit/jour#decision-{rank}` (ancres rendues côté Pilotage). Le P5 priorities (Risque financier réglementaire) renvoie sur `/cockpit/strategique?focus=exposure` pour drill-down ciblé.

## Confiance & traçabilité

Footer Sol affiche systématiquement : `Source · confiance · MAJ relative · méthodologie`. Cliquer "méthodologie" mène à ce document.

## Anti-patterns évités (doctrine §6.3)

- Pas de KPI 4ᵉ visible (triptyque inviolable)
- Pas d'acronyme brut (BACS / TURPE / ARENH / VNU / CBAM / CEE glossarisés via `<AcronymTooltip>`)
- Pas de chiffre € sans source (badges Calculé / Modélisé / Estimation / Indicatif obligatoires)
- Pas de magic number FE (EPEX pill masquée si null plutôt que valeur hardcodée)
- Pas de leak slug demo (scope HELIOS pur)

## Évolutions prévues (post-sprint)

- Connexion EPEX SPOT live → pill EPEX réapparaîtra avec cours day-ahead temps réel.
- V2 split sites : ranking €/MWh par site dans la facture portefeuille (audit Jean-Marc CFO P0).
- V2 export PDF CODIR (rapport COMEX cliquable génère PDF stocké).
