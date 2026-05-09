# Matrice de violations — Sprint Grammaire Produit v1 — Phase 0

_Capturé 2026-05-09 · branche `claude/refonte-sol2` · 8 vues × 10 lois Sol v1.1_

Légende : ✅ conforme · ⚠️ partiel (P1/P2) · ❌ violé (P0)

## Tableau

| Loi | Description | Cockpit Jour | Cockpit Stratégique | Centre d'action | Anomalies | Site360 Paris | Conformité | Factures | Onboarding | Conf/8 |
|---|---|---|---|---|---|---|---|---|---|---|
| **L1** | Hero préambule (anti-pattern §6.1) | ⚠️ P1 | ⚠️ P2 | ❌ P0 | ✅ | ❌ P0 | ✅ | ✅ | ❌ P0 | 3/8 |
| **L2** | Triptyque Fraunces / DM Sans / JetBrains Mono (§5) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 8/8 |
| **L3** | KPIs ≤ 3 + tooltip ? + footer source (§5) | ❌ P0 | ❌ P0 | ⚠️ P1 | ⚠️ P2 | ❌ P0 | ⚠️ P2 | ⚠️ P1 | ✅ | 1/8 |
| **L4** | Acronymes transformés (anti-pattern §6.3) | ⚠️ P2 | ❌ P0 | ⚠️ P1 | ✅ | ✅ | ❌ P0 | ❌ P0 | ❌ P0 | 2/8 |
| **L5** | Empty state contextualisé (anti-pattern §6.1) | ✅ | ✅ | ⚠️ P2 | ✅ | ✅ | ✅ | ✅ | ⚠️ P1 | 6/8 |
| **L6** | Footer Source · Confiance · Mis à jour (§5) | ❌ P0 | ❌ P0 | ❌ P0 | ⚠️ P1 | ⚠️ P1 | ⚠️ P1 | ❌ P0 | ⚠️ P1 | 0/8 |
| **L7** | Densité éditoriale 200 px (principe 4) | ⚠️ P1 | ✅ | ❌ P0 | ✅ | ⚠️ P1 | ⚠️ P2 | ⚠️ P1 | ✅ | 3/8 |
| **L8** | Kicker breadcrumb contextualisé (§5) | ✅ | ⚠️ P2 | ⚠️ P1 | ✅ | ⚠️ P2 | ✅ | ✅ | ❌ P0 | 4/8 |
| **L9** | Le produit pousse, ne tire pas (principe 6) | ⚠️ P1 | ⚠️ P2 | ❌ P0 | ⚠️ P2 | ⚠️ P1 | ✅ | ⚠️ P2 | ❌ P0 | 1/8 |
| **L10** | Cohérence chiffres cross-écrans (anti-pattern §6.4/§6.5) | ✅ | ✅ | ⚠️ P2 | ⚠️ P2 | ⚠️ P2 | ✅ | ✅ | ✅ | 5/8 |

| **Score doctrinal /10** | _verdict agent_ | 5.0/10 | 5.5/10 | 3.0/10 | 7.5/10 | 5.0/10 | 7.0/10 | 6.0/10 | 1.5/10 | **5.1/10** moyenne |

## Top 5 violations transverses (par nombre de P0/P1)

| # | Loi | Description | P0 | P1 | P2 | Conformes |
|---|-----|-------------|----|----|----|-----------|
| 1 | **L6** | Footer Source · Confiance · Mis à jour (§5) | 4 | 4 | 0 | 0/8 |
| 2 | **L4** | Acronymes transformés (anti-pattern §6.3) | 4 | 1 | 1 | 2/8 |
| 3 | **L3** | KPIs ≤ 3 + tooltip ? + footer source (§5) | 3 | 2 | 2 | 1/8 |
| 4 | **L1** | Hero préambule (anti-pattern §6.1) | 3 | 1 | 1 | 3/8 |
| 5 | **L9** | Le produit pousse, ne tire pas (principe 6) | 2 | 2 | 3 | 1/8 |

## Vues classées par dette doctrinale (P0 d'abord)

| Rang | Vue | P0 | P1 | P2 | Score /10 |
|------|-----|----|----|----|-----------|
| 1 | Onboarding (`onboarding`) | 5 | 2 | 0 | 1.5/10 |
| 2 | Centre d'action (`centre-action`) | 4 | 3 | 2 | 3.0/10 |
| 3 | Cockpit Stratégique (`cockpit-strategique`) | 3 | 0 | 3 | 5.5/10 |
| 4 | Site360 Paris (`site-paris-bureaux`) | 2 | 3 | 2 | 5.0/10 |
| 5 | Cockpit Jour (`cockpit-jour`) | 2 | 3 | 1 | 5.0/10 |
| 6 | Factures (`factures`) | 2 | 2 | 1 | 6.0/10 |
| 7 | Conformité (`conformite`) | 1 | 1 | 2 | 7.0/10 |
| 8 | Anomalies (`anomalies`) | 0 | 1 | 3 | 7.5/10 |


## Observations méthodologiques

- **L2 _Triptyque typo_** : 8/8 vues conformes. Les 3 polices Fraunces / DM Sans / JetBrains Mono sont déployées de manière homogène sur tout le repo (acquis Sprint 1 doctrine).
- **L3 _KPIs ≤ 3 + tooltip + source_** : initialement noté comme P0 par 7/8 agents. La taxonomie sépare deux choses : (a) **count** ≤ 3 KPIs above-fold est respecté sur la plupart des vues sauf Site360 (≥ 9 KPIs) ; (b) **tooltip "?" + source** absent quasiment partout (chevauche L6). La matrice ci-dessus traite L3 dans son acception "tooltip + source" (chevauche L6) et fait apparaître le mismatch L3/L6 comme la dette grammar la plus systémique.
- **L11 _Emplacement de brique_** (anti-pattern §6.4 + principe 11) : ajout spontané par l'agent C sur `/onboarding` qui sert en fait le Cockpit Stratégique. Ce mismatch URL/contenu n'apparaît dans aucune des 10 lois standard mais dépasse leur gravité — on le code en P0 critique dans la synthèse.

## Cellules notables (à lire en priorité)

- `centre-action × L7` ❌ P0 : journal brut sans hiérarchisation, 8 items quasi-identiques.
- `onboarding × L1/L8/L9/L11` ❌ P0 quadruple : la route ne sert pas un wizard mais le Cockpit Stratégique COMEX.
- `site-paris-bureaux × L1` ❌ P0 : 9 KPIs above-fold sans préambule — anti-pattern §6.1.
- `conformite × L4` ❌ P0 : `BACS GISMO/CTC`, `Loi APER (EN58)`, `Audit énergétique obligatoire à ISS` non transformés.
- `factures × L4` ❌ P0 : `TURPE 7`, `CSPE`, `TICFE`, `CTA`, `EDI`, `CIEE` bruts.
- `cockpit-jour × L6` ❌ P0 : aucun footer Source · Confiance · Mis à jour. Bloque crédibilité B2B.
