# PROMEOS — Vision Stratégique & Produit

> **Document de synthèse consolidée.** Réunit la doctrine stratégique (Vision Consolidée v1.3),
> la doctrine produit (PROMEOS Sol v1.1) et l'état de livraison du repo au 18 mai 2026.
>
> **Version** : 1.0 — consolidation 18/05/2026
> **Statut** : document de référence vivant. Toute évolution donne lieu à un versionnage explicite.
> **Sources cardinales** :
> - `project_promeos_vision_consolidee_v1_3_2026_05_08.md` (doctrine stratégique — supersède v1/v1.1/v1.2)
> - `docs/vision/promeos_sol_doctrine.md` (doctrine produit v1.1, addendum L11 du 09/05)
> - `CLAUDE.md` + ADR-025→029 (Centre d'Action V4)
> - Audit de l'état du repo au 18/05/2026
>
> **Public** : pitch investisseur seed (juin 2026), prospects commerciaux, onboarding équipe, arbitrages produit/archi/GTM.

---

## 0. Résumé exécutif — la vision en une page

**PROMEOS est le système de contrôle énergétique B2B des patrimoines multi-sites** — la *tour de contrôle énergétique du client B2B*.

Le marché de l'énergie B2B post-ARENH est devenu illisible : factures opaques, conformité réglementaire foisonnante (Décret Tertiaire, BACS, APER, Audit SMÉ, OPERAT), consommation non maîtrisée sur des parcs dispersés. Les outils existants (Deepki, Advizeo, Citron, Energisme, Schneider) sont conçus **par des ingénieurs pour des ingénieurs** — tableaux denses, jargon, écrans morts.

PROMEOS prend le pari inverse : un produit **pour les non-sachants d'abord** — dirigeants, DAF, directeurs immobilier/RSE — qui satisfait également les sachants. Il se lit comme un **journal hebdomadaire qui se réécrit chaque jour** : briefing éditorial, événements prioritaires, anomalies détectées, échéances réglementaires, fenêtres marché.

- **5 verbes cardinaux** : centraliser · fiabiliser · comparer · auditer · piloter.
- **Wedge d'entrée** : Facture + Conformité + Consommation.
- **Promesse finale** : *« Comprendre. Décider. Agir. Prouver. »*
- **Pricing 3 tiers** : Control Lite 6,9 k€ / Control 19,9 k€ / Control Plus per-site, + 4 extensions modulaires.
- **3 verticales prioritaires Y1-Y2** : tertiaire multi-sites privé · bailleurs · retail multi-sites.
- **Forecast Y3** : ~1,04 M€ ARR SaaS-only, ~1,2 M€ consolidé (revenue-share = bonus, jamais le cœur du BP).

PROMEOS **n'est pas** un hub Zapier, ni un fournisseur, ni un courtier, ni un agrégateur, ni une PMO ACC, ni un EMS vertical mono-archétype.

---

## 1. Positionnement cardinal

### 1.1 Les formulations canoniques

| Usage | Formulation |
|---|---|
| **Phrase canonique** | *« PROMEOS est le système de contrôle énergétique B2B des patrimoines multi-sites. »* |
| **Pitch 1 ligne** | *« PROMEOS est la tour de contrôle énergétique du client B2B. »* |
| **Pitch investisseur** | *« PROMEOS construit la couche de contrôle énergétique B2B post-ARENH. »* |
| **Promesse produit** | *« Comprendre. Décider. Agir. Prouver. »* |

### 1.2 Les 5 verbes cardinaux

1. **Centraliser** — réunir factures, contrats, conformité, consommation d'un parc dispersé dans une seule tour de contrôle.
2. **Fiabiliser** — nettoyer, normaliser, recouper les données ; signaler ce qui n'est pas fiable plutôt que de l'afficher faussement.
3. **Comparer** — benchmarks ADEME/OID par archétype, site vs site, fournisseur vs fournisseur, shadow billing vs facture réelle.
4. **Auditer** — détecter anomalies de facture, dérives de consommation, écarts réglementaires ; remonter à la source et à la formule.
5. **Piloter** — pousser au bon moment l'action prioritaire, le scénario chiffré, l'échéance, la fenêtre marché.

### 1.3 Le wedge — porte d'entrée

**Facture + Conformité + Consommation.** Trois douleurs immédiates, mesurables, à ROI lisible :
- une facture mal auditée coûte cher (anomalies TURPE/accise/CTA récupérables) ;
- une non-conformité Décret Tertiaire expose à 7 500 € de pénalité par site ;
- une consommation non pilotée dérive sans alerte.

Le wedge crée l'adhésion. Les extensions (Achat, Compliance+, ACC, Flex) montent ensuite en compte (*land & expand*).

### 1.4 Ce que PROMEOS n'est pas

| ❌ N'est pas | Pourquoi |
|---|---|
| Un hub Zapier | PROMEOS a des moteurs métier propres, pas de la plomberie d'intégration. |
| Un fournisseur d'énergie | Neutralité non-fournisseur = avantage durable. |
| Un courtier | Pas de marge cachée sur la fourniture ; transparence de rémunération. |
| Un agrégateur RTE | Bridge vers agrégateurs partenaires (Flex Advisory M&V only), pas d'effacement direct. |
| Une PMO d'autoconsommation collective | L'extension ACC outille la PMO **du client**, jamais PROMEOS comme PMO. |
| Un EMS vertical mono-archétype | Le « grand écart compatible » : un seul produit, tous archétypes. |

---

## 2. Marché & cible

### 2.1 Trois verticales prioritaires Y1-Y2

Servir 8 verticales en solo + agents = 8 cycles de vente, pas de PMF. Focalisation v1.3 :

| Rang | Verticale | Persona décideur | Canal d'acquisition | Pourquoi prioritaire |
|---|---|---|---|---|
| **P0** | Tertiaire multi-sites privé (entreprise / ETI) | DAF + Directeur RSE / immobilier | LinkedIn outbound · salons B2B · SEO « Décret Tertiaire » | Cœur OPERAT, doctrine déjà calibrée, budget rapide |
| **P0** | Bailleurs sociaux & privés tertiaires | DG + Directeur du patrimoine | USH · AORIF · ARELI · contenu « DT bailleurs » | Multi-sites natif, parc concerné DT, cycle 6-9 mois |
| **P1** | Retail multi-sites (>10 magasins) | Head of Facilities + DAF Groupe | Salons retail (PROCOS, FCD) · contenu « audit facture multi-sites » | Wedge facture immédiat, ROI lisible 60-90 j |

**Reportées vagues 2-3 (Y2+ post-PMF)** : collectivités (cycle public 12-18 mois), santé (ARS/GHT, exclusions process), enseignement public, agroalimentaire léger, logistique froide.

**Mathématiques cycle de vente** : 3 verticales × cycle 6-9 mois × funnel 5-10 % → 300-500 conversations qualifiées sur 24 mois (~12-21/mois) → cible **30-42 clients Y3**, réaliste pour un solo + 1-2 SDR partenaires.

### 2.2 Le non-sachant d'abord

La cible primaire est le **non-sachant** : dirigeant de PME/ETI qui n'a jamais lu un avenant ARENH, DAF qui découvre l'énergie, opérateur de site en début de fonction. Il n'a ni le temps ni l'envie d'apprendre les acronymes avant d'utiliser le produit — **le produit doit le prendre par la main**.

Le **sachant** (energy manager, ingénieur énergéticien) est servi par le même produit, sans friction : la profondeur (sources, formules, exports, données brutes) est **accessible en un clic mais invisible par défaut**. Asymétrie volontaire — le non-sachant servi par défaut, jamais l'inverse.

### 2.3 Positionnement concurrentiel

| Axe | Advizeo | Deepki | Citron | **PROMEOS Sol** |
|---|---|---|---|---|
| Storytelling éditorial | Faible | Moyen | Faible | **Fort (briefing journal)** |
| Non-sachant servi | Non (consultant) | Partiel | Non | **Oui (cible primaire)** |
| Bill Intelligence intégrée | Non | Non | Non | **Oui (shadow billing)** |
| Achat post-ARENH intégré | Partiel | Non | Non | **Oui** |
| Multi-archétype | Tertiaire focus | Tertiaire/ESG | Tertiaire/indus | **Tous archétypes** |
| Self-serve | 14 sem. onboarding | Variable | Variable | **Oui** |
| Conformité FR (DT/BACS/APER/SMÉ) | Bon | Bon | Bon | **Excellent (RegOps canonique)** |
| Flex monétisable | Non | Non | Non | **Oui (NEBCO + bridge)** |

**Argument commercial** : le seul produit français qui combine **facture + conformité + achat + flex** dans une UX éditoriale pour non-sachants, avec rigueur des sources B2B et infrastructure FR native.

**Moats durables** : (1) traçabilité réglementaire NOR + date + version sur chaque chiffre — aucun concurrent ne l'expose ; (2) polymorphisme produit assumé (cf. §5.5) ; (3) neutralité non-fournisseur transparente.

---

## 3. Modèle économique

### 3.1 Pricing — 3 tiers + Enterprise

| Offre | Prix | Cible | Périmètre |
|---|---|---|---|
| **PROMEOS Control Lite** | **6,9 k€/an** | 1-10 sites, mono-job | 1 module au choix : Facture **OU** Conformité **OU** Consommation ; ≤ 10 PRM/PCE ; cockpit lecture |
| **PROMEOS Control** | **19,9 k€/an** | 5-15 sites, multi-job | Full socle 5 verbes ; ≤ 15 PRM/PCE ; cockpit complet ; centre d'action |
| **PROMEOS Control Plus** | **19,9 k€ + per-site dégressif** | 16-50 sites | Tout Control + multi-EJ + reporting financier exécutif |
| **PROMEOS Enterprise** | **Custom négocié** | 50+ sites | Pricing per-MWh ou per-€-facture ; SLA renforcé ; account manager dédié |

**Barème per-site dégressif Control Plus** (anti-perception punitive) :

| Tranche | Tarif marginal | Exemple cumulé |
|---|---|---|
| 16-30 sites | +850 €/site/an | 30 sites → 19,9 + 12,75 = **32,65 k€/an** |
| 31-50 sites | +600 €/site/an | 50 sites → 32,65 + 12,0 = **44,65 k€/an** |
| 50+ sites | bascule **Enterprise custom** | per-MWh / per-€-facture |

Plafond Control Plus ~50 k€/an — au-delà, bascule Enterprise (évite la « facturation kilométrique » perçue comme punitive).

### 3.2 Extensions modulaires

| Extension | Fourchette cible | Note |
|---|---|---|
| **Purchase** | 4-8 k€/an + revenue-share 0,5-1 % FAS | Stratégie d'achat post-ARENH |
| **Compliance+** | 6-12 k€/an | Inclut horodatage **eIDAS qualifié** (Universign/Yousign Advanced, 3-5 k€/an absorbés) |
| **ACC** | 8-15 k€/an + frais projet | Outille la PMO **du client**, jamais PROMEOS PMO |
| **Flex Advisory** | 3-6 k€/an + revenue-share 5-10 % flex | M&V advisory only, bridge agrégateurs |

### 3.3 Doctrine financière cardinale

> **Les revenue-shares Achat et Flex sont des BONUS — jamais le cœur du BP.**
> Le BP doit tenir uniquement sur les 3 streams SaaS (Lite / Control / Plus + extensions).
> Si le revenue-share s'effondre (churn partenaire, requalification SCE), le BP reste viable.

### 3.4 Forecast Y3

| Mix client Y3 | Volume | ARPA | ARR |
|---|---|---|---|
| Lite seul | 15 | 8 k€ | 120 k€ |
| Control + 1 extension | 15 | 28 k€ | 420 k€ |
| Control + 2 extensions | 8 | 35 k€ | 280 k€ |
| Control Plus + 2-3 extensions | 4 | 55 k€ | 220 k€ |
| **TOTAL SaaS-only Y3** | **42 clients** | **~25 k€ moyen** | **~1,04 M€** |
| + revenue-share flex (~100-200 sites pilotables) | | | +60-100 k€ |
| + revenue-share achat (~20-30 contrats) | | | +30-60 k€ |
| **TOTAL consolidé Y3** | | | **~1,2 M€** (intervalle 1,1-1,4 M€) |

Compatible Pre-Seed 1,5-2 M€ Y1. Plus crédible que les forecasts historiques 1,6-3 M€.

### 3.5 Cadre juridique — 6 conditions cumulatives

1. DPO désigné + AIPD (RGPD — données de comptage = données personnelles côté occupants).
2. PMO ACC = le client, jamais PROMEOS.
3. Cashback énergie → toujours formulé en **remise sur facture**, jamais en versement.
4. Adhésion SCE (Système de Comptage d'Énergie / statut courtier) visée Q3 2026.
5. Bannir le mot **« neutre »** sans transparence de rémunération attenante.
6. Opinion légale annuelle sur le montage apporteur d'affaires + SaaS.

---

## 4. Doctrine produit — PROMEOS Sol

### 4.1 Vision en un paragraphe

PROMEOS Sol est un **OS énergétique vivant**, conçu d'abord pour les non-sachants et qui sait également satisfaire les sachants. Sol pousse à l'attention de ses utilisateurs les événements de leur patrimoine **au moment où ils ont du sens**. La solution se lit comme un **journal hebdomadaire qui se réécrit chaque jour** : briefing éditorial, événements prioritaires, signaux à surveiller, échéances réglementaires, fenêtres marché, anomalies détectées. La grammaire éditoriale reste invariante quel que soit le profil patrimoine. Chaque brique — Patrimoine, Conformité, Bill-Intel, Achat, Flex, Cockpit — a un impact fort et **tient debout comme produit autonome**. La complexité réglementaire et technique (TURPE 7, ATRD, DJU, CUSUM, NEBCO, ARENH) n'est ni cachée ni exposée — elle est **transformée** en récit, signal, opportunité.

### 4.2 Les 12 principes

| # | Principe | Test simple |
|---|---|---|
| 1 | **Le briefing au lieu du dashboard** — kicker → titre → narrative → puis les chiffres | Comprendre l'essentiel en lisant 3 lignes |
| 2 | **La navigation comme déambulation guidée** — le produit propose, ne fait pas chercher | 3 actions urgentes trouvées en < 30 s sans formation |
| 3 | **Le grand écart compatible** — un seul produit, tous archétypes (ETI 5 sites → groupe 200 sites) | Aucun archétype n'a l'impression que « ce n'est pas pour lui » |
| 4 | **La densité éditoriale impactante** — le vide est un bug | Jamais > 200 px de hauteur sans information utile |
| 5 | **Le glanceable summary** — savoir en 3 secondes si ça va ou pas | Screenshot 3 s → l'utilisateur résume l'état du patrimoine |
| 6 | **Le produit pousse, ne tire pas** — il pilote l'attention | 1-3 actions pertinentes suggérées à l'ouverture |
| 7 | **Le patrimoine vit, le produit suit** — l'app de J ≠ l'app de J+1 | Entre lundi et mardi, des cards changent d'état réellement |
| 8 | **Simplicité iPhone-grade** — apprentissage zéro, pas de manuel | Dirigeant PME opérationnel en < 3 min sans aide |
| 9 | **Chaque brique vaut un produit** — aucune feature insignifiante | Le module vendu standalone paierait-il un abonnement ? |
| 10 | **Transformer la complexité en simplicité** — ni cacher, ni exposer : transformer | Un non-sachant comprend la phrase principale sans glossaire |
| 11 | **Le bon endroit pour chaque brique** — mapping intention → emplacement limpide | Toute feature trouvée en < 2 clics |
| 12 | **Sachant et surtout non-sachant** — cible primaire = non-sachant | Expert et dirigeant trouvent leur valeur sans frustration |

### 4.3 Les 5 questions UX

Tout écran Sol doit répondre, dans l'ordre, à : **(1)** qu'est-ce que je regarde · **(2)** est-ce fiable · **(3)** quel est l'impact · **(4)** pourquoi · **(5)** quoi faire.

### 4.4 La grammaire éditoriale

```
[KICKER]                        ← contexte (mono, uppercase)
TITRE NARRATIF                  ← Fraunces, voix produit, phrase complète
Narrative 2-3 lignes            ← raconte ce qui se passe, sourcé et chiffré

[KPI 1] [KPI 2] [KPI 3]         ← 3 KPIs max, tooltip "?" + footer source

CETTE SEMAINE CHEZ VOUS         ← week-cards sémantiques typées
[À regarder] [À faire] [Bonne nouvelle]

CHARTS / TABLES / DRILL-DOWN    ← profondeur accessible à la demande

[FOOTER : SOURCE · CONFIANCE · MIS À JOUR]
```

**Triptyque typographique inviolable** : Fraunces (titres display) · DM Sans (corps) · JetBrains Mono (kickers, footers, KPIs tabular-nums). **Palette journal** : tons crème/brun chaleureux, jamais de corporate froid. **Marque** : toujours `PROMEOS` (5 lettres, majuscules, sans accent).

### 4.5 Loi L11 — Hub Page (addendum v1.1, 09/05/2026)

Chaque menu top-level (Énergie, Conformité, Facturation, Achat, Patrimoine) est une **page hub** : ni dashboard exhaustif, ni page vide. Gabarit obligatoire : kicker → hero titre → sous-ligne meta → **triptyque KPI (exactement 3)** → **2 graphes domaine (exactement 2)** → **3-5 highlights avec verbe d'invitation** → footer Source/Confiance/Mis à jour. Validation runtime stricte + source-guards CI.

**Polymorphisme produit** — différenciateur cardinal : la **Synthèse Stratégique** change de visage selon le profil patrimoine, via 5 régimes :

| Régime | Activation | Question centrale |
|---|---|---|
| Réglementaire | Décret Tertiaire applicable + trajectoire en retard | Comment caler trajectoire DT + audit obligatoire ? |
| Performance | Pas de contrainte légale, mais intensité élevée | Comment ramener le mauvais site au niveau du meilleur ? |
| Achat | Contrat à échéance proche / exposition spot élevée | Renouveler maintenant ou attendre ? |
| Opportunité | Ombrière APER + CEE valorisables | Quel levier activer en premier ? |
| Données insuffisantes | Patrimoine pas assez complété | Quels champs renseigner pour débloquer ? |

Le régime est calculé en cascade par le moteur d'assujettissement (ADR-024) qui vérifie l'applicabilité de 5 règles FR 2026 (DT, BACS, APER, SMÉ, BEGES) avec seuils versionnés. Aucun concurrent (Deepki, Metron, Akajoule) ne propose ce polymorphisme.

### 4.6 Les 5 règles de crédibilité

Pas de KPI magique · pas d'unité incohérente · pas de connecteur promis non livré · pas de neutralité sans transparence de rémunération · pas de recommandation sans source / formule / périmètre / impact.

---

## 5. Architecture produit

### 5.1 Architecture en 5 niveaux

1. **Référentiel patrimoine** — l'asset registry hiérarchique.
2. **Connecteurs critiques** — Enedis DataConnect, SGE SOAP, GRDF ADICT, parsers PDF facture/contrat.
3. **Moteurs métier** — scoring conformité, shadow billing, signature énergétique, flex scoring, priorisation d'actions.
4. **Cockpit client** — briefing éditorial, pages hub, centre d'action.
5. **Preuve & gouvernance** — traçabilité réglementaire, audit trail, horodatage eIDAS.

### 5.2 Modèle de données hiérarchique

```
Organisation → Entité Juridique → Portefeuille → Site → Bâtiment → Compteur → DeliveryPoint
```

Entités transverses : **Fournisseur** (référentiel hybride canonique/privé), **ContratCadre** (contrat-cadre EJ + annexes site N:N).

### 5.3 Règle d'or — zéro calcul métier frontend

Le frontend **affiche uniquement**. Tout calcul métier (CO₂, scoring, forecasting, trajectoires) est backend, exposé via REST, consommé en Context/hook. Conséquence : **une seule source de vérité par mesure**, aucune divergence possible entre écrans. SoT canoniques : `consumption_unified_service` (consommation), `regops/scoring.py` (conformité), `naf_resolver` (NAF), `emission_factors.py` (CO₂).

### 5.4 Stack technique

- **Backend** : Python 3.11 / FastAPI / SQLAlchemy / SQLite (PostgreSQL-ready) — port **8001**.
- **Frontend** : React 18 / Vite / Tailwind v4 / Recharts / Lucide — port **5173** (proxy → 8001).
- **Tests** : pytest (BE) · Vitest (FE) · Playwright (E2E) — baseline anti-régression intangible.

---

## 6. Les 7 piliers — rôle, promesse, état

| Pilier | Rôle | Promesse Sol | Différenciation | État au 18/05 |
|---|---|---|---|---|
| **Patrimoine** | Asset registry hiérarchique vivant | Votre patrimoine lisible comme un récit d'entreprise | Benchmarks ADEME OID + simulation mutualisation DT | ✅ Substantiel |
| **EMS / Énergie** | Monitoring, signature énergétique, anomalies, drill-down | Votre consommation devient une signature lisible | Carpet plot 24h×365j, CUSUM ISO 50001, anomalies ML (LOF+IsolationForest+SHAP), forecasting | ✅ Substantiel |
| **Conformité / RegOps** | Décret Tertiaire, BACS, APER, Audit SMÉ, OPERAT | La conformité devient une trajectoire claire | Trajectoire DT versionnée, scoring engine canonique, calculs sourcés NOR | ✅ Substantiel |
| **Bill Intelligence** | Audit factures, anomalies, contestations, reclaim | Chaque ligne de facture est challengeable | Shadow billing TURPE 7 / ATRD / accise / CTA, parser PDF EDF/Engie | ✅ Substantiel |
| **Achat** | Scénarios d'achat, échéances, hedging post-ARENH | Votre stratégie d'achat est anticipée | 30 fournisseurs CRE, wizard scénarios, prix EPEX, contexte VNU | ✅ Fonctionnel |
| **Flex** | Éligibilité NEBCO, Flex Score, bridge agrégateurs | Votre patrimoine peut générer des revenus de flexibilité | Diagnostic flex monétisé + bridge sans conflit d'intérêt | 🟡 Socle fonctionnel, intégration agrégateur Phase 3-4 |
| **Cockpit / CX** | Briefing exécutif + opérationnel, centre d'action | Aucun écran d'accueil mort | Briefing éditorial vivant réécrit chaque jour | ✅ Substantiel |

---

## 7. Centre d'Action V4 — chantier structurant Mois 1-6

Refonte lancée le **13/05/2026** : reconstruire le Centre d'Action sur un socle data propre, sécurisé, traçable.

**Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` (v0.3). **North star UX** : 5 maquettes HTML figées.

### 7.1 Concepts clés

- **2 axes orthogonaux** : `kind` (7 valeurs intrinsèques) ≠ `priority` (calcul dérivé P0-P3 + 6 règles de modulation R1-R6).
- **State machine lifecycle** : 5 états × 10 transitions strictes, 6 closure_reasons révisés.
- **Sécurité org-scoping** : 4 lignes de défense empilées (middleware + décorateur + repository org-scopé + source-guards CI), IDOR matrix 288 cellules.
- **Evidence & audit trail** : 16 event_types × 3 catégories de rétention RGPD, validation MIME par magic bytes (anti-spoofing).

### 7.2 Mois 1 — docs only, complet 10/10 ✅

| Livrable | Contenu |
|---|---|
| Doctrine v0.3 | Classement & priorisation, avenant Q37-A+ |
| L1 audit décisionnel | 86 verdicts binaires |
| ADR-025 Architecture V4 | 8 tables, 20 indexes, 100 tests |
| ADR-026 Migration data legacy → V4 | 9 invariants, cutover sécurisé Mois 4 |
| ADR-027 Sécurité org-scoping | 11 invariants, 8 menaces, 50 source-guards CI |
| ADR-028 Lifecycle states | State machine 5 états, 56 tests |
| ADR-029 Evidence + audit trail | 16 schemas Pydantic, 8 articles CNIL |
| L7 Data Dictionary V4 | Référence unique, 70 termes, 49 invariants |
| L8 Plan suppression legacy Mois 5 | 18 tables à DROP, STOP GATE 8 critères |
| L9 Manuel backend Mois 2 | 8 sprints, 50 source-guards, pyramide tests |

### 7.3 Mois 2 — backend (en cours)

Branche active `feat/m2-4-rollout`. Sprint M2-4 livré : V4 action-center opérationnel — **15 endpoints** (templates, sous-ressources lecture, écritures), modèles SQLAlchemy V4, repository org-scopé, IDOR matrix cross-org, seed idempotent.

| Sprint | Livraison |
|---|---|
| M2-1 | Foundation infra (structlog, deps, scaffolding) |
| M2-2 | 8 tables V4 + 9 enums + migration Alembic additive |
| M2-3 | Sécurité : `require_v4_role`, BaseRepository org-scopé, 5 source-guards |
| M2-4 | API : 15 endpoints (POST/GET items, sous-ressources, écritures), IDOR matrix |

**Suite** : M2-5 priority scoring · M2-6 intégration · Mois 4 cutover sécurisé (feature flag global + backup triple artefact + STOP GATE J+14) · Mois 5 suppression legacy.

---

## 8. État de livraison au 18/05/2026

### 8.1 Substantiellement livré ✅

- **6 piliers** avec implémentations réelles (EMS, RegOps, Bill Intelligence production-ready ; Achat, Flex, CX fonctionnels).
- **Modèle de données** complet : hiérarchie 6 niveaux + DeliveryPoint + **Fournisseur** + ContratCadre v2.
- **Fixes P0 v1.3 livrés** : entité `Fournisseur` (P0-1), parser PDF facture EDF/Engie (P0-2), parser PDF contrat (P0-3) — la roadmap pitch-ready v1.3 est exécutée.
- **Pages hub Sol** : Briefing du Jour (Phase 3.4), Synthèse Stratégique polymorphe 5 régimes (Phases 3.5-3.9), Cockpit Pilotage/Décision, Patrimoine, Site360, Conformité, Bill-Intel, Achat.
- **Centre d'Action V4** : Mois 1 docs 10/10, Mois 2 backend M2-4 (15 endpoints, sécurité org-scopée).
- **Tests** : baseline mature (BE plancher ~6 027, FE ~4 515+), source-guards anti-régression.

### 8.2 Dette résiduelle 🟡

- **Flex** : socle scoring + NEBCO en place, intégration API agrégateur réelle = Phase 3-4.
- **Synthèse Stratégique** : 6 valeurs €/MWh figées dans constructeurs à brancher sur les services facturation 12 mois glissants ; heuristique `atteint_pct` à remplacer par lecture détaillée des findings (3,5 j/h — non bloquant pilote).
- **Connecteurs Enedis/SGE/GRDF** : OAuth2 + parsers R6X + pipeline PHOTO à finaliser (chantier ε).
- **Moteur d'événements proactif** (chantiers α/β/γ) : la promesse « le produit pousse » reste partielle tant que le moteur de détection/priorisation/distribution n'est pas industrialisé.
- **Pages Sol legacy** : pages anciennes (Cockpit historique, CockpitPilotage) à déprécier au profit de l'architecture L11.

---

## 9. Roadmap

| Horizon | Chantiers |
|---|---|
| **Court terme (Mois 2-3)** | Centre d'Action V4 backend : M2-5 priority scoring, M2-6 intégration · fidélité chiffres Synthèse Stratégique (3,5 j/h) |
| **Mois 4** | Cutover sécurisé V4 — feature flag global, backup triple artefact J-1, STOP GATE J+14 |
| **Mois 5** | Suppression legacy (18 tables, ~1 667 LoC FE, STOP GATE 8 critères) |
| **Mois 6 (juillet 2026)** | Démo intégrale — 3 personas (investisseur · Jean-Marc CFO · Marie DAF tertiaire) |
| **Structurel 6-12 mois** | α moteur d'événements proactif · β multi-archétype dynamique · γ apprentissage user via tracker · δ transformation complexité→simplicité systématique · ε connecteurs Enedis/GRDF/SGE réels |
| **GTM Q3-Q4 2026** | Adhésion SCE · partenariat eIDAS (Universign/Yousign) · partenariats agrégateurs (Tilt, Flexcity) · pitch seed |

---

## 10. Definition of Done & jalons

### 10.1 Avant pitch investisseur Pre-Seed (juin 2026)

- [x] Fixes P0 repo livrés (Fournisseur + parsers PDF) → score livré ≥ 78 %.
- [ ] Phrase canonique testée sur 10 CFO froids → ≥ 50 % « bon », ≥ 25 % « excellent ».
- [ ] Pricing 3 tiers benchmarké via 5 entretiens prospects qualifiés.
- [ ] Partenariat eIDAS — LOI signée.
- [ ] 6 fixes P0/P1 régulatoires repo (org-scoping flex + data quality).

### 10.2 Avant industrialisation Y2

- [ ] **5 LOI signées** (engagement 50 €/mois, 6 mois) sur la formulation v1.3.
- [ ] **2 pilotes payés** Control Lite 6,9 k€, engagement renouvelable.
- [ ] **NPS pilote > 40** sur les 2 références terrain.
- [ ] Cashback énergie / Compte d'Épargne → greffe pillar Flex Advisory si LOI ≥ 5.

---

## 11. Risques & garde-fous

| Risque | Garde-fou |
|---|---|
| Pricing flat exclut 60 % de la cible | 3 tiers Lite/Control/Plus |
| 8 verticales = pas de PMF | 3 verticales prioritaires Y1-Y2 |
| Versionning OPERAT non opposable DREAL | Horodatage eIDAS qualifié, conservation 10 ans |
| Requalification SCE / churn partenaire | Revenue-share = bonus, BP tient sur SaaS pur |
| Calcul métier dérivant vers le frontend | Règle d'or zéro calcul FE + source-guards CI |
| Régression de baseline tests | Baseline intangible, source-guards, workflow pre-merge |
| Migration data legacy → V4 risquée | ADR-026 : 9 invariants, backup triple, STOP GATE J+14 |
| IDOR / fuite cross-org | ADR-027 : 4 lignes de défense, IDOR matrix 288 cellules |
| Promesse produit > livraison réelle | Matrice Pitch/Repo/Roadmap, mentions roadmap explicites en pitch |

---

## 12. La doctrine en une phrase

> **PROMEOS est la tour de contrôle énergétique du client B2B multi-sites :
> elle transforme la complexité réglementaire et tarifaire en récit lisible,
> pousse les bons signaux au bon moment, et permet de comprendre, décider, agir et prouver —
> non-sachants d'abord, sachants servis également.**

Toute décision produit, architecture, GTM ou pricing qui ne sert pas cette phrase n'a pas sa place dans PROMEOS.

---

**Document de synthèse v1.0 — 18/05/2026.**
Supersède en lisibilité (sans les remplacer) les docs sources cités en en-tête.
Toute évolution majeure → v1.1, v2.0 avec commit explicite.
