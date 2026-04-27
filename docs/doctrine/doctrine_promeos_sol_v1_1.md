# Doctrine PROMEOS Sol — version consolidée

> Document de référence produit, UX, data, métier et engineering.  
> Toute décision PROMEOS — feature, écran, copy, navigation, KPI, backend, intégration, test, release — doit pouvoir être justifiée au regard de cette doctrine.

**Version** : 1.1 consolidée  
**Date** : 2026-04-27  
**Statut** : doctrine opératoire — socle produit + règles d'exécution  
**Périmètre** : PROMEOS Sol / cockpit énergétique B2B post-ARENH  
**Principe cardinal** : tout est lié — patrimoine → données → KPIs → alertes → actions → conformité → factures → achat → flexibilité.

---

## 0. Verdict doctrinal

PROMEOS Sol doit devenir un cockpit énergétique B2B vivant, simple en surface, rigoureux en profondeur, conçu d'abord pour les non-sachants et crédible pour les sachants.

La doctrine initiale est cohérente et différenciante. Elle porte une vraie rupture : remplacer le dashboard technique par un briefing énergétique éditorial, sourcé et actionnable. Mais pour devenir une doctrine réellement utilisable par le produit et par le code, elle doit être renforcée par des règles d'exécution : qualité data, source de vérité, définition KPI, règles API, tests QA, critères de merge et limites de scope MVP.

Cette version consolidée conserve l'ambition initiale, mais ajoute la discipline nécessaire pour éviter trois risques majeurs :

1. une belle narration sans preuve métier ;
2. une promesse trop large impossible à livrer proprement ;
3. une UX élégante mais fragilisée par des données incohérentes.

PROMEOS Sol ne doit pas raconter l'énergie. Il doit **prouver**, **expliquer** et **faire agir**.

---

## 1. Pourquoi cette doctrine existe

Le marché des logiciels énergétiques B2B est encore largement dominé par des outils conçus par des experts pour des experts : tableaux denses, acronymes bruts, KPIs non définis, navigation arborescente, interfaces techniques, écrans morts, graphiques sans récit, actions peu évidentes.

Ces outils peuvent être puissants, mais ils imposent à l'utilisateur de comprendre l'énergie avant de comprendre le produit.

PROMEOS Sol prend le pari inverse : rendre l'énergie B2B compréhensible, actionnable et crédible sans appauvrir la vérité métier.

Le produit doit servir :

- le dirigeant ou DAF qui veut savoir ce qui se passe, combien cela coûte et quoi décider ;
- le responsable énergie qui veut vérifier les calculs, les sources, les écarts et les trajectoires ;
- l'opérateur de site qui veut comprendre les actions à mener ;
- le consultant ou expert qui veut auditer, exporter, challenger et approfondir ;
- l'organisation multisite qui veut passer de la donnée dispersée au pilotage structuré.

La doctrine existe pour empêcher PROMEOS de devenir un dashboard de plus. Elle existe aussi pour empêcher l'excès inverse : un produit joli, narratif, mais insuffisamment robuste pour le B2B énergie.

---

## 2. Vision en une phrase

**PROMEOS Sol est un cockpit énergétique B2B vivant qui transforme les données, factures, obligations réglementaires et signaux marché en décisions simples, sourcées et actionnables.**

Le produit sert d'abord les non-spécialistes — dirigeants, DAF, responsables de site, opérateurs métier — tout en donnant aux experts l'accès aux calculs, sources, exports, preuves et logs.

Sa promesse :

> Chaque utilisateur comprend en quelques secondes ce qui se passe, pourquoi c'est important, combien cela vaut, et quoi faire ensuite.

---

## 3. Vision longue

PROMEOS Sol est un OS énergétique vivant pour les organisations B2B françaises post-ARENH. Il pousse à l'attention des utilisateurs les événements importants de leur patrimoine énergétique au moment où ils ont du sens : dérives de consommation, anomalies facture, échéances réglementaires, risques contractuels, opportunités d'achat, fenêtres de flexibilité, incohérences de données, actions prioritaires.

La solution se lit comme un briefing hebdomadaire qui se réécrit chaque jour : titres éditoriaux, signaux prioritaires, cartes d'événements, KPIs sourcés, actions recommandées, explications simples et profondeur technique accessible à la demande.

PROMEOS Sol ne cache pas la complexité réglementaire, tarifaire ou technique. Il ne l'expose pas brute non plus. Il la transforme en récit opérationnel, en signal priorisé et en décision vérifiable.

La simplicité vient de la surface : peu de choix, peu de friction, peu de jargon, priorité claire.  
La crédibilité vient de la profondeur : sources, formules, unités, périmètres, périodes, versions réglementaires, logs et preuves.

---

## 4. Positionnement marché

### 4.1 Cible primaire : les non-sachants

Le non-sachant est la cible primaire de PROMEOS Sol.

Exemples :

- dirigeant de PME ou ETI qui n'a pas le temps d'apprendre les mécanismes énergie ;
- DAF qui découvre l'énergie dans une nouvelle fonction ;
- directeur immobilier ou patrimoine qui doit piloter des sites sans être énergéticien ;
- responsable RSE/QHSE qui doit suivre conformité et trajectoire ;
- élu, DGS ou responsable technique de collectivité qui doit arbitrer budget, conformité et travaux ;
- exploitant de site qui doit agir sans lire un rapport de 40 pages.

Ces utilisateurs ne veulent pas devenir experts énergie. Ils veulent savoir :

- où est le risque ;
- où est l'argent ;
- où est l'urgence ;
- quelle action est prioritaire ;
- qui doit faire quoi ;
- quelle preuve soutient la recommandation.

### 4.2 Cible secondaire : les sachants

Le sachant est servi par le même produit, sans créer une seconde interface complexe.

Exemples :

- energy manager ;
- ingénieur efficacité énergétique ;
- consultant énergie ;
- acheteur énergie ;
- responsable exploitation / GTB ;
- analyste facture ou marché.

Ces utilisateurs doivent pouvoir :

- ouvrir le calcul ;
- vérifier la source ;
- exporter les données ;
- voir les hypothèses ;
- contrôler les unités ;
- challenger les écarts ;
- comprendre la version réglementaire utilisée.

**Asymétrie volontaire** : le non-sachant est servi par défaut. Le sachant accède à la profondeur en un clic. Pas l'inverse.

### 4.3 Différenciation

PROMEOS Sol défend une position nette :

> Le cockpit énergétique B2B qui combine lisibilité grand public, rigueur métier, conformité française, intelligence facture, stratégie d'achat et orientation action.

La différence ne doit pas être uniquement déclarative. Elle doit être prouvée par le produit.

| Axe | Approche classique marché | Doctrine PROMEOS Sol |
|---|---|---|
| Accueil | Dashboard KPI | Briefing priorisé |
| Cible | Expert énergie | Non-sachant d'abord, expert ensuite |
| Complexité | Exposée ou cachée | Transformée |
| KPI | Affiché | Défini, sourcé, expliqué |
| Conformité | Tableau d'obligations | Trajectoire + preuves + actions |
| Facture | PDF ou historique | Shadow billing + écarts + contestation |
| Achat | Comparaison ponctuelle | Scénarios + échéances + risques |
| Actions | Liste isolée | Centre d'action relié aux événements |
| Données | Visuelles | Gouvernées, qualifiées, traçables |

---

## 5. Limite stratégique : ambition forte, MVP discipliné

PROMEOS Sol peut viser un OS énergétique complet, mais le MVP ne doit pas essayer de tout livrer en même temps.

### 5.1 Wedge recommandé MVP

Le wedge prioritaire est :

1. **Patrimoine + données** ;
2. **Consommation / performance** ;
3. **Conformité réglementaire** ;
4. **Bill Intelligence légère** ;
5. **Centre d'action**.

Pourquoi ce wedge :

- douleur immédiate ;
- valeur compréhensible par les non-sachants ;
- crédibilité B2B forte ;
- base data nécessaire aux futures briques ;
- liens naturels vers achat, ACC et flexibilité.

### 5.2 Briques futures

Les briques Achat, ACC, Flex et stockage doivent être pensées dès maintenant dans l'architecture, mais pas surpromises dans le MVP.

La bonne formulation :

> PROMEOS Sol commence par sécuriser la donnée, la conformité, la performance et la facture. Puis il étend naturellement vers l'achat, l'autoconsommation collective, la flexibilité et les systèmes locaux et personnalisés.

---

## 6. Les 13 principes PROMEOS Sol

### Principe 1 — Le briefing au lieu du dashboard

Un dashboard classique affiche des KPIs et laisse l'utilisateur décider où regarder. PROMEOS Sol oriente.

Chaque page importante doit répondre :

- que se passe-t-il ?
- pourquoi est-ce important ?
- quel est l'impact ?
- quelle action est recommandée ?
- quelle source le prouve ?

**Règle** : une page ne commence pas par un tableau ou une grille KPI sans préambule.

**Test** : un utilisateur comprend le sujet principal en lisant les trois premières lignes.

---

### Principe 2 — La navigation comme déambulation guidée

PROMEOS propose plus qu'il ne fait chercher.

Le produit guide vers les sections importantes du jour ou de la semaine : dérives, échéances, factures suspectes, sites prioritaires, actions ouvertes, opportunités.

**Règle** : l'utilisateur doit trouver les trois priorités de son patrimoine en moins de 30 secondes.

**Anti-pattern** : menus profonds, routes invisibles, doublons de navigation, pages orphelines.

---

### Principe 3 — Le grand écart compatible

Un même produit doit servir des patrimoines très différents : PME mono-site, ETI tertiaire, groupe industriel, hôtellerie, collectivité, bailleur, agroalimentaire.

L'interface reste cohérente, mais les récits, benchmarks, KPIs et actions s'adaptent à l'archetype.

**Règle** : ne jamais afficher un KPI, un benchmark ou une copy qui suppose un type de site si le patrimoine ne le justifie pas.

---

### Principe 4 — La densité utile, pas le remplissage

Le vide est un signal produit, mais il ne doit pas devenir du remplissage.

Une page PROMEOS doit être dense en informations utiles, mais jamais bruyante. Si une zone est vide, elle est remplacée par un message contextualisé, une prochaine action, une explication ou elle est masquée.

**Bonne pratique** : “Aucune anomalie détectée cette semaine sur 5 sites. Prochaine échéance OPERAT dans 68 jours.”

**Mauvaise pratique** : “Aucune donnée disponible.”

---

### Principe 5 — Le glanceable summary

L'utilisateur doit savoir en 3 secondes si la situation va bien, ce qui mérite attention et ce qu'il peut décider.

Le premier fold d'une page importante doit contenir :

1. une synthèse narrative ;
2. 1 à 3 KPIs maximum ;
3. une action prioritaire ;
4. une source et une date de mise à jour.

---

### Principe 6 — Le produit pousse, ne tire pas

PROMEOS doit piloter l'attention.

L'utilisateur n'a pas à aller chercher seul les anomalies, échéances, risques ou opportunités. Le produit détecte, priorise et pousse les signaux pertinents.

**Règle** : aucun signal critique ne doit rester uniquement dans une table profonde ou une sous-page.

---

### Principe 7 — Le patrimoine vit, le produit suit

L'application du lundi ne doit pas être identique à celle du mardi si les données, échéances ou événements changent.

Le produit doit refléter la vie du patrimoine : données reçues, données manquantes, dérives, contrats, factures, obligations, actions, décisions.

**Règle** : les cards, priorités et statuts doivent évoluer à partir d'événements réels, jamais de randomisation.

---

### Principe 8 — Simplicité iPhone-grade

La simplicité n'est pas une esthétique. C'est une réduction radicale de la friction cognitive.

PROMEOS doit pouvoir être compris sans formation pour les fonctions essentielles.

**Règle** : aucune page cœur ne doit nécessiter de lire une documentation externe pour comprendre ce qu'elle dit.

---

### Principe 9 — Chaque brique doit créer une preuve de valeur

Chaque module doit pouvoir justifier son existence par une valeur claire : réduction coût, réduction risque, conformité, gain de temps, meilleure décision, action opérationnelle.

On ne crée pas une feature pour “faire complet”.

**Test** : si le module était vendu seul, quelle preuve de valeur le client accepterait-il de payer ?

---

### Principe 10 — Transformer la complexité en simplicité

PROMEOS ne cache pas TURPE, ATRD, BACS, OPERAT, accise, DJU, CUSUM, NEBCO, HP/HC, kVA, kWh, MWh ou €/MWh.

Il les transforme.

Exemples :

- au lieu de “écart TURPE HPH”, dire : “votre facture applique une puissance plus coûteuse sur les heures d'hiver — impact estimé : 4 200 €/an” ;
- au lieu de “thermosensibilité DJU”, dire : “chaque degré sous 18 °C ajoute environ 320 kWh/jour à ce site” ;
- au lieu de “éligibilité NEBCO”, dire : “ce site pourrait être rémunéré s'il réduit temporairement sa consommation lors de périodes réseau tendues”.

La profondeur reste disponible via “voir le calcul”.

---

### Principe 11 — Le bon endroit pour chaque brique

Toute information doit être au bon endroit dans l'architecture.

| Intention utilisateur | Emplacement naturel |
|---|---|
| Comprendre la situation globale | Cockpit |
| Voir les sites, bâtiments, compteurs | Patrimoine |
| Suivre consommation et performance | Consommation / Performance |
| Gérer obligations, preuves et échéances | Conformité |
| Comprendre ou contester une facture | Bill Intelligence |
| Anticiper contrat, prix, renouvellement | Achat |
| Identifier effacement, flex, optimisation | Flex / Optimisation |
| Suivre les décisions | Centre d'action |

**Règle** : une feature critique doit être trouvable en moins de deux clics.

---

### Principe 12 — Non-sachant d'abord, sachant respecté

Le non-sachant doit comprendre sans prérequis. Le sachant doit pouvoir vérifier sans frustration.

**Règle** : chaque information importante a deux niveaux :

- niveau 1 : lecture simple, décisionnelle ;
- niveau 2 : calcul, source, hypothèses, export, logs.

---

### Principe 13 — Une information n'existe que si elle est fiable ou explicitement incertaine

PROMEOS ne doit jamais afficher une valeur comme vraie si elle est estimée, incomplète ou incohérente.

Chaque donnée importante doit être :

- sourcée ;
- datée ;
- rattachée à un périmètre ;
- exprimée dans une unité explicite ;
- qualifiée par un niveau de confiance ;
- explicable.

**Règle d'or** : pas de KPI magique.

---

## 7. Contrat de confiance data

PROMEOS Sol repose sur un contrat de confiance avec l'utilisateur.

### 7.1 Toute donnée affichée doit porter une identité

Pour chaque KPI, valeur ou alerte :

- source : Enedis, GRDF, facture, GTB, IoT, saisie manuelle, RegOps, marché, benchmark ;
- période : jour, mois, année, contrat, échéance ;
- périmètre : organisation, portefeuille, site, bâtiment, compteur ;
- unité : kWh, MWh, kW, kVA, €, €/MWh, kgCO₂e, %, jours ;
- statut : réel, estimé, incomplet, à confirmer, incohérent ;
- dernière mise à jour ;
- confiance : haute, moyenne, faible.

### 7.2 Statuts obligatoires

| Statut | Signification | UX attendue |
|---|---|---|
| Réel | Donnée issue d'une source primaire fiable | Affichage normal |
| Estimé | Donnée calculée ou extrapolée | Badge “estimé” + explication |
| Incomplet | Période ou périmètre partiel | Badge “partiel” + données manquantes |
| Incohérent | Divergence entre sources | Alerte + action de correction |
| En attente | Connecteur ou import non finalisé | État de progression |
| Démo | Donnée fictive ou seed | Badge visible “donnée démo” |

### 7.3 Interdits data

- fallback silencieux ;
- valeur mockée sans badge ;
- conversion implicite ;
- unité absente ;
- comparaison entre périodes différentes sans le dire ;
- mélange HT/TTC non explicité ;
- source multiple non arbitrée ;
- KPI calculé différemment selon les pages.

---

## 8. Doctrine KPI

Aucun KPI PROMEOS ne peut exister sans fiche de définition.

### 8.1 Fiche KPI obligatoire

Chaque KPI doit documenter :

```yaml
kpi_id: annual_consumption_mwh
label: Consommation annuelle
unit: MWh
formula: sum(consumption_kwh) / 1000
source: consumption_unified_service
scope: site | portfolio | organization
period: rolling_12_months | calendar_year | contract_year
freshness: daily | monthly | on_import
confidence_rule: high_if_full_period_and_primary_source
owner: data_product
used_in:
  - cockpit
  - portfolio
  - site
  - conformity
  - bill_intelligence
```

### 8.2 KPIs prioritaires du cockpit

Le cockpit ne doit pas afficher 15 indicateurs. Les KPIs prioritaires sont :

1. consommation ;
2. coût ;
3. trajectoire / objectif ;
4. qualité data ;
5. actions ouvertes ;
6. risque conformité ;
7. anomalies facture ou dérives.

Les autres indicateurs doivent être accessibles en profondeur, pas en premier niveau.

---

## 9. Grammaire éditoriale PROMEOS Sol

Toute page cœur suit une grammaire stable.

```text
[KICKER CONTEXTUEL]
Titre narratif clair
Narrative courte : ce qui se passe, pourquoi c'est important, impact.

[KPI 1] [KPI 2] [KPI 3]
Source, période, confiance.

Cette semaine chez vous
[À regarder] [À faire] [Bonne nouvelle ou risque maîtrisé]

Détails / graphes / tableaux / preuves

Footer : source · confiance · dernière mise à jour · voir le calcul
```

### 9.1 Règles de copy

- Pas d'acronyme brut en titre.
- Pas de phrase décorative.
- Pas de promesse sans preuve.
- Pas de chiffre sans unité.
- Pas de recommandation sans source ou hypothèse.
- Toujours dire quoi faire ensuite quand une anomalie ou un risque est affiché.

### 9.2 Ton

Le ton doit être :

- clair ;
- calme ;
- expert ;
- actionnable ;
- jamais alarmiste gratuitement ;
- jamais marketing creux.

Exemple acceptable :

> Votre site de Lyon consomme 18 % de plus que sa baseline météo sur les 14 derniers jours. L'écart représente environ 1 240 € si la dérive se prolonge sur un mois. Vérifiez les horaires CVC et les consignes de week-end.

Exemple interdit :

> Une anomalie énergétique a été détectée. Veuillez consulter le tableau de bord.

---

## 10. Modèle d'événement énergétique

Le produit vivant repose sur un moteur d'événements.

```ts
type SolEventCard = {
  id: string;
  event_type:
    | "consumption_drift"
    | "billing_anomaly"
    | "compliance_deadline"
    | "contract_renewal"
    | "market_window"
    | "data_quality_issue"
    | "flex_opportunity"
    | "asset_registry_issue"
    | "action_overdue";

  severity: "info" | "watch" | "warning" | "critical";
  title: string;
  narrative: string;

  impact: {
    value: number | null;
    unit: "€" | "kWh" | "MWh" | "kW" | "kVA" | "kgCO2e" | "days" | "%";
    period: "day" | "week" | "month" | "year" | "contract" | "deadline";
  };

  source: {
    system: "Enedis" | "GRDF" | "invoice" | "GTB" | "IoT" | "RegOps" | "EPEX" | "manual" | "benchmark";
    last_updated_at: string;
    confidence: "high" | "medium" | "low";
  };

  action: {
    label: string;
    route: string;
    owner_role?: "DAF" | "Energy Manager" | "Site Manager" | "Admin" | "Operator";
  };

  linked_assets: {
    org_id: string;
    portfolio_id?: string;
    site_ids?: string[];
    building_ids?: string[];
    meter_ids?: string[];
    invoice_ids?: string[];
    contract_ids?: string[];
  };
};
```

Un événement PROMEOS est valide seulement s'il répond :

- quel fait l'a déclenché ?
- quel périmètre est concerné ?
- quel impact est estimé ?
- quelle action est possible ?
- quelle source le prouve ?
- quel niveau de confiance est associé ?

---

## 11. Architecture fonctionnelle cible

PROMEOS Sol s'organise autour de modules reliés, pas de silos.

### 11.1 Patrimoine

Rôle : référentiel vivant du patrimoine.

Hiérarchie cible :

```text
Organisation → Entité juridique → Portefeuille → Site → Bâtiment → Compteur → Donnée / Facture / Contrat
```

Règle : tout KPI, alerte, action, facture ou obligation doit être rattaché à un élément du patrimoine.

### 11.2 Data & qualité

Rôle : sécuriser les flux, les imports, les connecteurs, les statuts et la confiance.

PROMEOS doit accepter la réalité terrain : fichiers Excel, factures PDF, GTB hétérogènes, API Enedis, systèmes locaux et personnalisés, compteurs incomplets, données retardées.

Règle : la complexité d'intégration doit être absorbée par le produit, pas subie par l'utilisateur final.

### 11.3 Consommation / Performance

Rôle : comprendre et expliquer la consommation.

Fonctions : baseline, météo, DJU, dérive, baseload, horaires, usages, anomalies, signatures de charge, performance multisite.

Règle : toute dérive doit être reliée à un impact et à une action.

### 11.4 Conformité

Rôle : transformer obligations et preuves en trajectoire lisible.

Périmètre : Décret Tertiaire / OPERAT, BACS, APER, audit énergétique, futures règles applicables.

Règle : aucune obligation ne doit être affichée sans statut, échéance, preuve, responsable et prochaine action.

### 11.5 Bill Intelligence

Rôle : rendre la facture compréhensible, contrôlable et contestable.

Fonctions : lecture facture, shadow billing, écarts, taxes, acheminement, puissance, index, régularisations, contestation.

Règle : chaque anomalie facture doit être reliée à une ligne, une période, un compteur, une règle et une action.

### 11.6 Achat énergie

Rôle : anticiper contrats, risques, scénarios et décisions post-ARENH.

Fonctions : échéances, comparaison fixe/indexé/spot, scénarios, exposition marché, alertes renouvellement, préparation consultation.

Règle : achat doit être connecté aux consommations réelles, aux factures et au patrimoine.

### 11.7 Flex / Optimisation

Rôle : identifier les actifs pilotables et les opportunités de flexibilité.

Fonctions : flex score, effacement potentiel, IRVE, CVC, froid, stockage, signaux marché, agrégateurs.

Règle : ne jamais promettre un revenu flex sans hypothèse claire, seuil, contrainte et niveau de confiance.

### 11.8 Centre d'action

Rôle : unifier ce qui doit être fait.

Toute anomalie, obligation, facture suspecte, risque contrat, action terrain ou correction data doit remonter dans un hub actionnable.

Règle : PROMEOS ne doit pas disperser les actions dans chaque module sans consolidation.

---

## 12. Règles API et backend

### 12.1 Endpoints cœur

```http
GET /api/sol/briefing
GET /api/sol/events?scope=portfolio&period=week
GET /api/sol/kpis?scope=site&site_id=...
GET /api/sol/actions
GET /api/sol/data-quality
GET /api/sol/sources/:source_id
GET /api/sol/explain/:event_id
GET /api/sol/assets/:asset_id/context
GET /api/sol/compliance/status
GET /api/sol/billing/anomalies
```

### 12.2 Standard d'erreur API

```json
{
  "code": "DATA_QUALITY_INCOMPLETE_PERIOD",
  "message": "La consommation annuelle ne couvre pas une période complète.",
  "hint": "Importez les données manquantes de janvier à mars ou affichez ce KPI en statut partiel.",
  "correlation_id": "req_01HX...",
  "scope": {
    "site_id": "site_123",
    "meter_id": "meter_456"
  }
}
```

### 12.3 Interdits backend / frontend

Interdit :

- calcul KPI dans le frontend ;
- logique réglementaire dans le frontend ;
- conversion d'unités dispersée ;
- fallback silencieux ;
- mock non marqué ;
- endpoint différent pour la même mesure ;
- comparaison de données non alignées en période ;
- règles réglementaires non versionnées ;
- logs contenant des données sensibles.

---

## 13. Anti-patterns explicites

### 13.1 Anti-patterns UX

- page qui commence par un tableau sans synthèse ;
- écran vide sans prochaine action ;
- notification orpheline ;
- KPI affiché sans source ;
- graphique sans période ;
- filtre qui ne modifie pas réellement les données ;
- bouton sans destination cohérente ;
- route accessible uniquement par URL ;
- page identique semaine après semaine malgré événements nouveaux.

### 13.2 Anti-patterns métier

- kWh et MWh mélangés ;
- kW et kVA confondus ;
- €/kWh et €/MWh non explicités ;
- HT/TTC non indiqué ;
- période facture et période consommation mélangées ;
- valeur conformité sans règle source ;
- score sans formule ;
- benchmark non adapté à l'activité ;
- recommandation sans impact.

### 13.3 Anti-patterns produit

- ajouter un menu au lieu d'améliorer le centre d'action ;
- créer une feature sans preuve de valeur ;
- créer un module qui ne tient pas seul ;
- dupliquer une information dans deux modules avec valeurs différentes ;
- cacher une information critique pour “alléger l'écran” ;
- utiliser du storytelling pour masquer une donnée faible.

---

## 14. Tests doctrinaux

### Test 1 — Les 3 secondes

Un screenshot est montré 3 secondes. L'utilisateur doit dire si la situation est bonne, mauvaise ou à surveiller.

### Test 2 — Le dirigeant non-sachant

Un dirigeant non expert ouvre PROMEOS. En moins de 3 minutes, il doit comprendre :

- ce qui se passe ;
- ce qui coûte ;
- ce qui risque ;
- quoi faire.

### Test 3 — Le sachant

Un expert doit pouvoir vérifier :

- formule ;
- source ;
- unité ;
- période ;
- périmètre ;
- hypothèses ;
- export.

### Test 4 — La cohérence transverse

La même consommation, le même coût ou le même statut conformité doivent être identiques entre Cockpit, Portfolio, Site, Conformité, Bill Intelligence et Achat.

### Test 5 — La densité utile

Aucune zone principale ne doit être vide sans explication ou prochaine action.

### Test 6 — J vs J+1

Si un événement réel a changé, l'écran doit le refléter.

### Test 7 — L'emplacement

Une feature critique est trouvable en moins de deux clics.

### Test 8 — La preuve de valeur

Chaque module doit produire une preuve client claire : économie, risque réduit, temps gagné, conformité sécurisée, décision facilitée.

---

## 15. Checklist QA zéro issue

### Front / UX

- [ ] Loading, empty, error, partial data et offline traités.
- [ ] Pas d'acronyme brut en titre.
- [ ] Source et date visibles pour les KPIs clés.
- [ ] Les filtres sont visibles, réinitialisables et actifs.
- [ ] Les graphes affichent unité, période, source et légende.
- [ ] Les actions mènent à une route réelle.
- [ ] Responsive validé mobile/tablette/desktop.
- [ ] Accessibilité clavier et contrastes validés.

### Back / API

- [ ] Validation server-side des inputs.
- [ ] Unités normalisées et conversions centralisées.
- [ ] Erreurs standardisées avec `code`, `message`, `hint`, `correlation_id`.
- [ ] Logs utiles sans données sensibles.
- [ ] Règles réglementaires versionnées.
- [ ] Endpoints documentés.
- [ ] Tests unitaires des calculs.
- [ ] Tests d'intégration des endpoints critiques.

### Data / métier

- [ ] Chaque KPI a définition, formule, source, unité, période, périmètre.
- [ ] Les valeurs sont cohérentes entre vues.
- [ ] Les données estimées ou partielles sont clairement indiquées.
- [ ] Les anomalies sont rattachées à un actif et une source.
- [ ] Les obligations conformité ont échéance, responsable, preuve et action.
- [ ] Les factures sont rattachées à compteur, contrat et période.

### Release

- [ ] Aucune route morte.
- [ ] Aucun bouton non fonctionnel.
- [ ] Aucun mock non signalé.
- [ ] Aucune régression KPI.
- [ ] Aucun écran sans état vide utile.
- [ ] Tests e2e sur parcours dirigeant, energy manager et admin data.

---

## 16. Governance engineering

Toute PR significative doit inclure une section doctrine.

```markdown
## Doctrine compliance

- Principes respectés : 1, 5, 10, 13
- Risques ou tensions : données partielles sur le site X
- KPI impactés : annual_consumption_mwh, energy_cost_eur
- Sources utilisées : Enedis, facture fournisseur, RegOps
- Tests ajoutés : unit KPI, integration API, e2e cockpit
- États UX couverts : loading, empty, error, partial data
```

### Critères de rejet d'une PR

Une PR doit être rejetée si :

- elle crée un KPI sans fiche ;
- elle calcule une règle métier dans le frontend ;
- elle affiche une valeur sans unité ;
- elle introduit une route morte ;
- elle ajoute une action non reliée à un objet métier ;
- elle casse la cohérence entre vues ;
- elle masque une donnée incertaine comme certaine.

---

## 17. Roadmap doctrine

### P0 — Socle MVP

- référentiel patrimoine propre ;
- KPIs unifiés ;
- cockpit briefing ;
- conformité principale ;
- consommation / performance ;
- qualité data visible ;
- centre d'action ;
- premiers contrôles facture.

### P1 — Crédibilité B2B

- shadow billing approfondi ;
- conformité avec preuves ;
- moteur d'événements ;
- connecteurs robustes ;
- exports experts ;
- logs et traçabilité ;
- scénarios achat simples.

### P2 — Best-in-world

- assistant éditorial énergétique ;
- adaptation par archetype ;
- intelligence achat post-ARENH ;
- flex score ;
- ACC starter ;
- systèmes locaux et personnalisés ;
- recommandations automatiques multi-modules.

---

## 18. Definition of Done produit

PROMEOS Sol est conforme à cette doctrine quand :

1. un non-sachant comprend le cockpit en moins de 3 minutes ;
2. un expert peut vérifier chaque KPI ;
3. les mêmes valeurs sont cohérentes entre toutes les vues ;
4. chaque événement affiché vient d'un fait réel ou d'un calcul explicite ;
5. chaque action est reliée à un actif, une source et un impact ;
6. les données incertaines sont visibles comme incertaines ;
7. aucune page n'est morte ;
8. aucun KPI n'est magique ;
9. le produit reste simple sans devenir superficiel ;
10. le storytelling sert la décision, jamais l'habillage.

---

## 19. Doctrine en une phrase finale

> PROMEOS Sol transforme la complexité énergétique B2B en décisions simples, sourcées et actionnables : non-sachants d'abord, sachants respectés, zéro KPI magique, zéro écran mort, zéro donnée non qualifiée.

Toute décision produit qui ne sert pas cette phrase doit être questionnée, simplifiée ou supprimée.
