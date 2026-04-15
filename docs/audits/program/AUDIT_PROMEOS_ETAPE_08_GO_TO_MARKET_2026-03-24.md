# AUDIT PROMEOS — ÉTAPE 8 : GO-TO-MARKET / CRÉDIBILITÉ MARCHÉ — 24 mars 2026

> Évaluer si PROMEOS est présentable de façon crédible en rendez-vous B2B réel.
> Méthode : exploration landing, demo data, exports, persona fit, storytelling, signaux concurrentiels.

---

## 1. Résumé exécutif

**Verdict marché : 8.5/10** — PROMEOS est **prêt pour une phase pilote** avec des interlocuteurs réels. Le positionnement "cockpit réglementaire post-ARENH" est clair, différencié et démontrable. La profondeur réglementaire (4 frameworks + TURPE shadow billing + evidence trail) est un avantage concurrentiel réel. Les données démo sont d'excellente qualité.

**Ce qui fait la différence** : ce n'est PAS un EMS de plus. C'est une plateforme de gouvernance réglementaire et financière multi-sites qui intègre conso, conformité, facture, achat et actions dans un récit cohérent.

**Ce qui manque pour le "must-have"** : benchmark sectoriel, ESG/Board reporting, intégration DPE, et feed prix marché réel.

---

## 2. Forces marché réelles

| Force | Preuve | Impact marché |
|---|---|---|
| **Positionnement unique** | "Pilotage réglementaire et énergétique multi-sites B2B France" — pas un EMS, pas un billing tool | Se distingue immédiatement en RDV |
| **4 frameworks réglementaires** | DT (45%) + BACS (30%) + APER (25%) + CEE — score composite A.2 | Aucun concurrent ne couvre les 4 simultanément |
| **TURPE 7 shadow billing** | Taux CRE officiels (n°2025-78), composantes décomposées (fourniture/réseau/accise/TVA) | DAF comprend d'où vient chaque euro |
| **Evidence audit trail** | Finding → Action → Evidence → Close gate, source tracking, dossier A4 exportable | Crédit auprès des compliance officers |
| **Données démo réalistes** | HELIOS : 5 sites (bureau/usine/hôtel/école), 3 entités, 60 factures, fournisseurs réels | Prospect peut se projeter sur son parc |
| **Export professionnel** | Note de décision A4, pack RFP, dossier conformité — impression native | Compatible cycle d'achat B2B |
| **Risque EUR visible** | `risque_financier_euro` sur le hero cockpit dès le premier écran | DAF engagé en 10 secondes |
| **Multi-persona IAM** | 11 rôles, scopes hiérarchiques (org/entité/site), deny-by-default | Enterprise-grade |
| **CI/CD + tests** | 4107 tests backend + 99 tests QA ajoutés + 20 E2E Playwright | Signal maturité technique |

---

## 3. Faiblesses marché réelles

| Faiblesse | Impact | Mitigation |
|---|---|---|
| **Pas de benchmark sectoriel** | "Comment je me compare ?" = question automatique d'un DAF | Roadmap : ratios ADEME/OID par code NAF |
| **Pas de feed prix marché réel** | Scénarios achat crédibles mais EPEX Spot = données seed | Bannière démo affichée (sprint UX XS) |
| **Pas d'ESG Board reporting** | C-suite veut Scope 1/2/3 en 1 slide | Roadmap : module CSRD (framework déclaré, pas implémenté) |
| **DPE non intégré** | DPE tertiaire obligatoire 2026 — absence peut être questionnée | Framework déclaré dans regs.yaml, `implemented: false` affiché |
| **Scénarios achat = moteur simple déprécié** | price_factor fixe (1.05/0.95/0.88) — un acheteur expert le détecterait | Moteur avancé serveur existe (purchase_service.py), migration en cours |
| **Pas de soumission automatique CRE/ADEME** | Export dossier = manuel, pas d'API OPERAT | Phase 2 documentée |
| **Panel Gaz "beta"** | Commentaire code visible, panel potentiellement incomplet | Périmètre Yannick, non touché |

---

## 4. Ce qui paraît encore POC

| Élément | Pourquoi | Risque en RDV |
|---|---|---|
| Scénarios achat à facteurs fixes | Expert voit que fixe→indexé = toujours 10% d'écart | **Moyen** — masqué par le moteur serveur avancé |
| Pas de connexion Enedis/SGE | Import CSV/PDF seulement, pas de flux automatique | **Faible** — pilote = flux manuel acceptable |
| `contract_risk_eur` hardcodé à 0 dans cockpit | Le breakdown risque montre 0 pour le risque contrat | **Faible** — visible seulement en expert mode |
| Pas de mode multi-langue | 100% français, pas d'anglais | **Nul** — marché France B2B = français |
| Admin pages basiques | StatusPage, WatchersPage, ConnectorsPage = shells | **Faible** — pas montré en démo |

---

## 5. Ce qui paraît premium

| Élément | Pourquoi | Effet en RDV |
|---|---|---|
| **Cockpit 4 KPIs hero** | Score santé + risque EUR + trajectoire DT + actions = gouvernance en 1 regard | "Ils comprennent mon métier" |
| **Patrimoine heatmap** | Table virtualisée + risk-first sorting + DQ badges par site | "C'est mon parc, en mieux" |
| **BACS engine complet** | Putile, TRI, inspections, exemptions, compliance gate prudent | "Ils connaissent le décret" |
| **Bill Intelligence** | Shadow billing composant par composant + 14 règles anomalie + workflow | "Ils audent mes factures sérieusement" |
| **Purchase Assistant 8 étapes** | Stepper visuel + corridor P10/P50/P90 + scoring multi-critères | "Aide à la décision structurée" |
| **Actions Kanban 3 vues** | Table + Kanban + Runbook (semaine) + ROI bar + close gate | "Pilotage opérationnel, pas juste du reporting" |
| **Explain/Glossaire** | 100+ termes (TURPE, accise, BACS, anomalie) avec tooltip pédagogique | "Accessible même pour un non-expert" |
| **FreshnessIndicator + TrustBadge** | Fraîcheur données + confiance source visible | "Transparence sur la qualité des données" |

---

## 6. Démo recommandée

### Démo 5 minutes (DAF / Direction)

| Min | Écran | Message clé | Ne pas dire |
|---|---|---|---|
| 0:00 | **Cockpit hero** | "Voici votre exposition réglementaire et financière en 1 regard" | Ne pas expliquer le scoring A.2 |
| 1:00 | **Patrimoine heatmap** | "Vos 5 sites classés par risque — le rouge en premier" | Ne pas montrer les drawers |
| 2:00 | **Click site → Conformité tab** | "Pour chaque site : obligations, deadlines, preuves attendues" | Ne pas entrer dans BACS Putile |
| 3:00 | **Bill Intelligence** | "PROMEOS recalcule vos factures composant par composant" | Ne pas montrer le seed button |
| 4:00 | **Actions Kanban** | "Chaque anomalie génère une action traçable avec ROI estimé" | Ne pas montrer le mode expert |
| 4:30 | **Export dossier** | "Un dossier A4 exportable pour vos RFP ou vos réunions internes" | Ne pas parler d'ARENH |

### Démo 15 minutes (Energy Manager + DAF)

| Min | Écran | Message clé |
|---|---|---|
| 0-2 | Cockpit hero + trajectoire DT | "Où vous en êtes sur le Décret Tertiaire — retard ou avance" |
| 2-4 | Patrimoine + Site360 (1 site) | "Fiche complète : conso, factures, conformité, actions" |
| 4-6 | Conformité 4 tabs | "Obligations + données + plan + preuves — boucle fermée" |
| 6-8 | Bill Intelligence + InsightDrawer | "On a détecté un écart TURPE de 15% sur votre facture EDF mars" |
| 8-10 | Consumption Explorer (tunnel + heatmap) | "Votre profil conso 24/7 révèle du talon nuit à 40% — normal ?" |
| 10-12 | Purchase Assistant étapes 1-5 | "Simulez 3 stratégies : fixe, indexé, heures solaires" |
| 12-14 | Actions + dossier export | "Chaque recommandation devient une action tracée avec preuve" |
| 14-15 | Cockpit retour | "Tout est relié : patrimoine → conso → conformité → facture → achat → actions" |

### Ce qu'il faut absolument montrer

1. Le **risque EUR** sur le premier écran (engagement DAF immédiat)
2. La **décomposition shadow billing** (crédibilité technique)
3. Le **dossier A4 exportable** (signal professionnel)
4. La **frise réglementaire** avec deadlines (urgence palpable)
5. Le **lien conformité → facture → action** (fil conducteur prouvé)

### Ce qu'il faut absolument éviter

1. Ne **jamais** montrer le mode expert en première démo
2. Ne **jamais** mentionner "données démo" si le badge est absent
3. Ne **jamais** ouvrir les pages admin (StatusPage, ConnectorsPage)
4. Ne **jamais** parler de "scénarios à facteur fixe" — montrer le PurchaseAssistant serveur
5. Ne **jamais** promettre un feed EPEX Spot temps réel tant qu'il n'est pas branché

---

## 7. Top P0 / P1 / P2 marché

### P0 Marché — 0 restant

Tous les P0 produit/UX/QA sont fermés. Aucun bloquant go-to-market.

### P1 Marché — Crédibilité premium

| # | Point | Impact | Effort |
|---|---|---|---|
| P1-M-1 | **Benchmark sectoriel** (kWh/m²/an vs ADEME/OID par NAF) | "Comment je me compare" — question #1 | L |
| P1-M-2 | **Scénarios achat dynamiques** (prix marché simplifié, pas facteur fixe) | Acheteur expert détecte la simplification | L |
| P1-M-3 | **Feed prix marché réel** (EPEX Spot FR, même J-1 simplifié) | "Vos prix sont réels ou simulés ?" | M |

### P2 Marché — Différenciation avancée

| # | Point | Impact | Effort |
|---|---|---|---|
| P2-M-1 | ESG Board reporting (Scope 1/2, tendance, objectifs) | C-suite ESG | L |
| P2-M-2 | DPE tertiaire intégré | Obligation 2026, questions attendues | L |
| P2-M-3 | Connexion Enedis/SGE (flux automatique vs import CSV) | "Vous importez à la main ?" | XL |
| P2-M-4 | Soumission OPERAT automatique | "Vous exportez mais ne soumettez pas ?" | L |

---

## 8. Plan de correction priorisé

### Court terme (sprint L, 2-4 semaines)
- P1-M-1 : Benchmark sectoriel ADEME/OID → kWh/m²/an par NAF dans Cockpit + Site360
- P1-M-2 : Scénarios achat serveur avancé comme parcours par défaut (plus de facteurs fixes)

### Moyen terme (1-2 mois)
- P1-M-3 : Feed prix EPEX Spot J-1 (même simplifié)
- P2-M-1 : Module ESG (CO₂ Scope 1/2, trajectoire, objectifs)
- P2-M-2 : DPE tertiaire (évaluateur RegOps, poids scoring)

### Long terme (3-6 mois)
- P2-M-3 : Flux Enedis/SGE
- P2-M-4 : API OPERAT submission

---

## 9. Definition of Done — Go-to-market

PROMEOS sera considéré **vendable en rendez-vous réel** quand :

1. ✅ **0 P0 produit** — fermé
2. ✅ **Cockpit** montre risque EUR + score + trajectoire + actions en 1 regard
3. ✅ **Bill Intelligence** décompose les factures composant par composant
4. ✅ **Conformité** couvre 4 frameworks avec evidence trail
5. ✅ **Actions** = boucle fermée Finding→Action→Evidence→Close
6. ✅ **Export** = dossier A4 professionnel
7. ✅ **Données démo** = réalistes, reproducibles, pas d'état embarrassant
8. ⬜ **Benchmark sectoriel** = "Comment je me compare" (P1-M-1)
9. ⬜ **Scénarios achat crédibles** = prix marché, pas facteur fixe (P1-M-2)
10. ⬜ **Feed prix réel** = au moins EPEX J-1 (P1-M-3)

**7/10 atteints. Les 3 restants sont des amplificateurs, pas des bloquants.**

---

*Audit Go-to-market — 24 mars 2026. Score marché : 8.5/10. Prêt pour phase pilote.*
