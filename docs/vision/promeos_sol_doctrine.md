)

# Doctrine PROMEOS Sol

> Document de référence produit. Toute décision PROMEOS — feature, écran, copy, navigation, KPI, backend, intégration — doit pouvoir être justifiée au regard de cette doctrine.
>
> **Version** : 1.0.1
> **Date** : 2026-04-26 (v1.0) · 2026-04-26 patch v1.0.1 (triptyque typographique aligné code)
> **Statut** : socle. Toute évolution donne lieu à un versionnage explicite (1.1, 2.0, etc.).
>
> **Changelog v1.0.1** (patch §11.1 « précision rédactionnelle ») :
>
> - §5 et §6.1 : triptyque typographique = `Fraunces + DM Sans + JetBrains Mono` (au lieu de `Fraunces + Inter + IBM Plex Mono`).
> - **Rationale** : Inter est devenu le font B2B SaaS générique (Vercel, Linear, Stripe) — l'inverse du signal éditorial Sol recherché. DM Sans porte mieux la voix journal. JetBrains Mono est techniquement supérieur pour les chiffres tabular-nums CFO (testé sur score 56px gauge Cockpit). Les 3 fonts sont déjà chargées (`frontend/index.html:11`, `frontend/src/ui/sol/tokens.css:13-15`). Aligner doctrine sur code = 0 dette technique.

---

## Préambule — pourquoi ce document existe

PROMEOS construit un produit B2B énergétique ambitieux dans un marché où la concurrence (Advizeo, Deepki, Citron, Energisme, Spacewell, Schneider Resource Advisor+, Trinergy, Homeys) propose massivement des outils pensés **par des ingénieurs pour des ingénieurs**. Tableaux denses, jargon non vulgarisé, KPIs sans définition, navigation arborescente, pages mortes, écrans techniques.

PROMEOS Sol prend le pari inverse : un produit pour les **non-sachants d'abord**, qui satisfait également les sachants. Un produit qui **vit** avec son utilisateur, qui pousse les bons signaux au bon moment, et qui transforme la complexité réglementaire et technique en récit lisible par tous.

Cette doctrine fixe les 12 principes qui guident toutes les décisions produit. Elle n'est pas négociable au cas par cas — elle évolue par versions, pas par exception.

---

## 1. Vision en un paragraphe

PROMEOS Sol est un OS énergétique vivant, conçu d'abord pour les non-sachants — dirigeants PME, DAF non-spécialistes énergie, opérateurs de site en début de fonction — et qui sait également satisfaire les sachants. Sol pousse à l'attention de ses utilisateurs B2B les événements de leur patrimoine au moment où ils ont du sens. La solution se lit comme un journal hebdomadaire qui se réécrit chaque jour : briefing éditorial, événements prioritaires, signaux à surveiller, échéances réglementaires, fenêtres marché, anomalies détectées. La grammaire éditoriale (kicker contextuel, titre narratif, narrative sourcée, KPIs avec tooltips, week-cards sémantiques) reste invariante quel que soit le profil patrimoine — ETI tertiaire 5 sites, groupe industriel agroalim 200 sites, hôtellerie multi-marques, collectivité multi-écoles. Chaque brique du produit — Patrimoine, Conformité, Bill-Intel, Achat, Flex, Cockpit — a un impact fort, une expérience révolutionnaire, et tient debout comme produit autonome. La complexité réglementaire et technique (TURPE 7, ATRD, DJU, CUSUM, NEBCO, ARENH) n'est ni cachée ni exposée — elle est transformée en récit, en signal, en opportunité. La crédibilité B2B vient de la rigueur des sources (RegOps, ADEME, EPEX) et de la densité éditoriale. La simplicité iPhone-grade vient de l'absence de friction cognitive — l'écran dit l'essentiel en 3 secondes, la complexité reste accessible mais invisible par défaut. Sol est un produit qui vit avec son utilisateur, qui transforme la complexité en simplicité, et qui rend l'énergie B2B compréhensible par tous.

---

## 2. Positionnement marché

### 2.1 Cible primaire : les non-sachants

Le **non-sachant** est la cible primaire de PROMEOS Sol :

- Dirigeant de PME ou ETI qui n'a jamais lu un avenant ARENH
- DAF qui découvre l'énergie en arrivant dans une nouvelle fonction
- Opérateur de site en début de fonction RSE/QHSE
- Investisseur ETI qui veut comprendre la trajectoire énergétique sans formation préalable
- Collaborateur d'un cabinet de conseil non-spécialiste énergie

Ces utilisateurs partagent une caractéristique : **ils n'ont ni le temps ni la disponibilité d'apprendre les acronymes énergétiques avant d'utiliser le produit**. Le produit doit les prendre par la main.

### 2.2 Cible secondaire : les sachants

Le **sachant** est servi par le même produit, sans friction supplémentaire :

- DAF avec 10 ans d'expérience énergie B2B
- Ingénieur énergéticien qui lit TURPE 7 dans le texte
- Energy manager industriel
- Consultant spécialisé en stratégie énergétique B2B

Ces utilisateurs trouvent leur valeur dans la **profondeur accessible à la demande** : sources citées, calculs explicites, exports détaillés, challenge des chiffres, accès brut aux données.

**Asymétrie volontaire** : le non-sachant est servi par défaut, le sachant accède à la profondeur en un clic. Pas l'inverse.

### 2.3 Différenciation concurrentielle

| Concurrent                  | Positionnement perçu                                                          | PROMEOS Sol vs concurrent                                          |
| --------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Advizeo / savee             | Energy Copilot + Explorer multi-points, modèle conseil 14 semaines onboarding | Sol : self-serve éditorial, pas de consultant requis               |
| Deepki                      | Conformité tertiaire + ESG enterprise                                         | Sol : bill intelligence + purchasing intégrés (Deepki ne fait pas) |
| Citron / iQspot             | Asset management énergétique, dashboard technique                             | Sol : briefing vivant vs dashboard statique                        |
| Energisme                   | Plateforme data, peu de UX produit final                                      | Sol : produit fini pour utilisateur métier, pas plateforme         |
| Schneider Resource Advisor+ | Enterprise, ingénieurs énergéticiens                                          | Sol : non-sachants, dirigeants, ETI                                |
| Trinergy                    | Convergence bill+purchasing belge entrant France                              | Sol : équivalent + storytelling éditorial + multi-archetype        |
| Homeys                      | Native Enedis/GRDF, France-fit, opérateur                                     | Sol : positionnement plus large que collecte                       |

**PROMEOS Sol défend** : le seul produit B2B énergie qui se lit comme un magazine spécialisé et qui rend l'énergie accessible aux dirigeants non-sachants tout en satisfaisant les ingénieurs.

---

## 3. Les 12 principes

### Principe 1 — Le briefing au lieu du dashboard

Un dashboard classique aligne 47 KPIs et laisse l'utilisateur choisir où regarder. Un briefing oriente : voici ce qui mérite votre attention aujourd'hui, voici pourquoi, voici ce que vous pouvez faire.

Sol propose un fil narratif éditorial : kicker de contexte → titre éditorial → 2-3 lignes qui racontent ce qui se passe → seulement ensuite les chiffres. L'utilisateur est guidé dans son parcours, pas largué devant un mur de data.

**Test simple** : un utilisateur arrivant sur la page sans préparation comprend l'essentiel en lisant les 3 premières lignes.

**Anti-pattern** : page qui commence par un tableau, une grille de KPIs, ou un graphique sans préambule.

### Principe 2 — La navigation comme déambulation guidée

Le produit propose plus qu'il ne fait chercher. Le rail Sol guide vers les sections importantes du jour ou de la semaine. Les week-cards orientent vers les actions prioritaires. Les deep-links amènent vers des vues filtrées pertinentes. Les pins et récents apprennent les habitudes.

C'est l'inverse d'une nav arborescente où l'utilisateur doit savoir ce qu'il cherche. Sol propose ce qu'il faut regarder.

**Test simple** : un utilisateur qui ouvre PROMEOS pour la première fois trouve les 3 actions les plus urgentes de son patrimoine en moins de 30 secondes sans formation.

**Anti-pattern** : menus à 4 niveaux, sous-pages cachées, chemins multiples pour atteindre la même information.

### Principe 3 — Le grand écart compatible

Un même produit Sol doit servir lisiblement :

- ETI tertiaire 5 sites (bureaux + école + hôtel + entrepôt mélangés)
- Groupe industriel agroalim 200 sites avec procédés énergivores
- Hôtellerie multi-marques avec saisonnalité forte
- Collectivité multi-écoles avec contraintes budgétaires publiques
- PME mono-site qui découvre l'énergie

Pas 5 produits différents. Un seul produit avec des vues qui s'adaptent à l'archetype : narrative générée selon profil patrimoine, KPIs prioritaires variables, benchmarks adaptés, vocabulaire ajusté.

**Test simple** : la même copie de PROMEOS Sol sert un DAF tertiaire et un dirigeant industriel sans qu'aucun des deux n'ait l'impression que le produit "n'est pas pour lui".

**Anti-pattern** : interfaces mono-archetype implicites (KPI tertiaire affiché à un industriel, copy "vos bureaux" pour une usine, benchmark ADEME bureau pour un site agroalim).

### Principe 4 — La densité éditoriale impactante

Aucune zone vide. Aucune notification orpheline. Aucune card "0 résultats" qui prend toute la largeur. Aucun écran "N/A 0 kWh chargement". Aucun message simple qui prend toute la place pour ne dire quasi rien.

**Le vide est un bug.** Si une section serait vide, elle est densifiée par un fallback contextuel, ou collapsée, ou remplacée par un message dense qui apporte de la valeur ("portefeuille stable cette semaine, 5 sites OPERAT à jour, prochaine échéance dans 68 jours").

**Test simple** : sur n'importe quelle page Sol, dans n'importe quel état du patrimoine, il n'y a pas plus de 200 pixels de hauteur sans information utile.

**Anti-pattern** : panneau "Aucune action" qui occupe 600px de hauteur, week-card "Bonne nouvelle : rien à signaler" sans contextualisation.

### Principe 5 — Le glanceable summary

L'utilisateur doit savoir en 3 secondes : est-ce qu'aujourd'hui ça va ou pas ? Qu'est-ce qui mérite mon attention en priorité ? Qu'est-ce que je peux décider ou déléguer ?

Sans cliquer, sans dérouler, sans dépasser le premier fold. L'écran d'accueil dit l'essentiel.

**Test simple** : screenshot du Cockpit montré 3 secondes à un utilisateur, qui résume immédiatement l'état de son patrimoine.

**Anti-pattern** : pages où l'information critique est sous le fold, où il faut survoler un graphique pour comprendre, où il faut interpréter une couleur pour savoir si c'est bon ou pas.

### Principe 6 — Le produit pousse, ne tire pas

Le produit pilote l'attention. L'utilisateur ne pilote pas l'exploration.

C'est un changement radical de paradigme par rapport aux dashboards classiques. Le produit anticipe ce qui mérite l'attention parce qu'il connaît le patrimoine, l'historique, les anomalies en cours, les échéances réglementaires, les fenêtres marché.

**Test simple** : un utilisateur qui ouvre l'app sans question préalable se voit suggérer 1 à 3 actions ou observations qui correspondent réellement à ses priorités du moment.

**Anti-pattern** : interface "neutre" qui se contente d'afficher le patrimoine sans hiérarchiser ce qui mérite attention.

### Principe 7 — Le patrimoine vit, le produit suit

Une refonte Décret Tertiaire entrée en vigueur, un site qui dérive de baseline, un contrat qui arrive à 30 jours, une fenêtre marché EPEX baissière, une nouvelle obligation BACS, une anomalie facture détectée hier soir, un rapport OPERAT à transmettre dans 159 jours.

Tous ces événements doivent surgir dans l'interface au moment où ils ont du sens. Pas attendre que l'utilisateur pense à vérifier. Pas être noyés dans un "Centre de notifications" générique.

**L'app de jour J n'est pas l'app de jour J+1.** C'est un flux d'événements pertinents, pas un état figé.

**Test simple** : entre lundi matin et mardi matin, plusieurs cards et signaux ont changé d'état, de priorité ou de contenu — pas par randomisation mais par évolution réelle.

**Anti-pattern** : page identique semaine après semaine, données figées, événements traités après leur péremption.

### Principe 8 — Simplicité iPhone-grade

Apple ne fait pas "joli interface". Apple fait réduction radicale de la friction cognitive : pas de manuel, apprentissage zéro pour les fonctions de base, l'enfant et le retraité utilisent la même interface.

Pour PROMEOS Sol, simplicité iPhone-grade signifie : un DAF B2B, un opérateur de site, un dirigeant de PME, un investisseur ETI doivent comprendre l'essentiel sans formation, sans tooltip lu, sans documentation.

L'écran d'accueil dit l'essentiel dans les 3 premières secondes. Aucune surcharge cognitive — pas de "47 KPIs scintillants", pas de "12 dropdowns à explorer". La complexité métier reste disponible mais invisible par défaut sauf si l'utilisateur le demande.

**Test simple** : un dirigeant de PME qui n'a jamais vu PROMEOS, ouvre l'app pour la première fois, comprend l'essentiel et sait quoi faire en 3 minutes max sans aide externe.

**Anti-pattern** : produit qui requiert un onboarding 14 semaines, un consultant dédié, ou la lecture d'une documentation pour être utilisable.

### Principe 9 — Chaque brique vaut un produit

Aucune feature insignifiante. Si une fonctionnalité n'a pas d'impact fort, elle ne devrait pas exister.

Chaque module du produit — Patrimoine, Conformité, Bill-Intel, Achat, Flex, Cockpit — doit pouvoir tenir comme produit autonome qu'on pourrait vendre seul, mais qui s'enrichit dans l'OS Sol.

**Test simple** : si on extrayait Conformité de PROMEOS et qu'on le vendait standalone, suffirait-il à payer un abonnement ? Si oui, le module est aligné doctrine. Si non, il est trop léger.

**Anti-pattern** : feature ajoutée pour "faire le total", checkbox utile pour 3 utilisateurs marginaux, sous-module redondant avec un autre.

### Principe 10 — Transformer la complexité en simplicité

Pas cacher la complexité (qui crée des produits jolis mais inopérants pour les sachants).
Pas exposer la complexité (qui crée des produits puissants mais incompréhensibles pour les non-sachants).

**Transformer** la complexité.

TURPE 7, ATRD, accise, CTA ne disparaissent pas — ils deviennent un récit dans Bill-Intel : "vous payez 47 € de plus que le tarif réglementé sur l'accise février 2026 — voici pourquoi".

DJU base température, modèles 3P/4P/5P, CUSUM ISO 50001 ne disparaissent pas — ils deviennent une signature énergétique lisible : "votre site est thermosensible — chaque degré sous 18°C ajoute 320 kWh/jour".

NEBCO, créneaux J-1 9h30 → J 22h, contraintes hausse ≤ baisse 7j/2j ne disparaissent pas — elles deviennent une opportunité monétisable : "votre site est éligible à 4 200 €/an de revenus flexibilité — voici les conditions".

C'est de la **vulgarisation experte**. La rigueur technique reste sourcée et accessible (clic sur "voir le calcul"). Mais la surface de l'écran parle humain.

**Test simple** : un utilisateur non-sachant lit la phrase principale d'une page et comprend ce qu'elle veut dire sans glossaire externe.

**Anti-pattern** : acronymes bruts dans les titres, formules mathématiques exposées, copy qui suppose la connaissance préalable des notions.

### Principe 11 — Le bon endroit pour chaque brique

Toute brique doit trouver sa place et être au bon endroit, visible et compréhensible.

C'est un principe architectural :

- Pas de feature enfouie 3 niveaux dans un menu
- Pas de feature redondante dans 2 modules différents
- Pas de feature critique invisible faute de vouloir "ne pas surcharger"
- Si une brique compte, elle doit être à un endroit où l'utilisateur la trouve sans effort

Le mapping intention → emplacement doit être limpide :

| L'utilisateur pense à...                         | Il trouve dans... |
| ------------------------------------------------ | ----------------- |
| Régulation, conformité, échéances réglementaires | Conformité        |
| Facture, anomalie, contestation                  | Bill-Intel        |
| Contrat, achat, négociation                      | Achat             |
| Mes sites, mes bâtiments, mes compteurs          | Patrimoine        |
| Aujourd'hui, cette semaine, vue d'ensemble       | Cockpit           |
| Effacement, revenus flexibilité                  | Flex              |

**Test simple** : l'utilisateur trouve une feature en moins de 2 clics depuis n'importe quelle page sans recherche.

**Anti-pattern** : feature accessible uniquement via URL directe, fonctionnalité dupliquée dans plusieurs modules sans raison, item de nav orphelin sans destination claire.

### Principe 12 — Sachant et surtout non-sachant

Le test de l'utilisateur double.

Le **sachant** doit pouvoir creuser, vérifier sources, exporter calculs, challenger les chiffres.

Le **non-sachant** doit comprendre ce qu'il doit faire et pourquoi sans aucune notion préalable.

**Surtout** non-sachant. Le non-sachant est la cible primaire. Le sachant trouvera son chemin (il est compétent par définition). Le non-sachant doit être pris par la main.

C'est l'inverse de 90% des SaaS B2B énergie aujourd'hui qui sont conçus par des ingénieurs pour des ingénieurs.

**Test simple** : 2 personnes utilisent PROMEOS — l'une expert énergie, l'autre dirigeant non-sachant. Les deux trouvent leur valeur sans frustration.

**Anti-pattern** : interface où le non-sachant ne sait pas par où commencer, où chaque tooltip suppose une notion préalable, où la complexité réglementaire est exposée brute.

---

## 4. Les 7 piliers PROMEOS

PROMEOS Sol s'incarne dans 7 modules. Chacun doit respecter les 12 principes ci-dessus tout en remplissant son rôle métier spécifique.

### 4.1 Patrimoine — Asset registry vivant

**Rôle** : organisation hiérarchique du patrimoine (Organisation → Entité juridique → Portefeuille → Site → Bâtiment → Compteur → Reading).

**Promesse Sol** : votre patrimoine est lisible comme un récit d'entreprise. EUI vs ADEME, surfaces, contrats, conformité — tout est mis en perspective dans une narrative qui parle de votre business.

**Différenciation** : benchmarks ADEME ODP 2024 systématiques par typologie + simulation mutualisation Décret Tertiaire (économie 23 k€ potentielle multi-sites) — feature unique dans le marché B2B multisite.

### 4.2 EMS / Énergie — Performance et diagnostics

**Rôle** : monitoring, signature énergétique, anomalies, drill-down portefeuille → site → bâtiment → compteur.

**Promesse Sol** : votre consommation devient une signature lisible. Thermosensibilité, baseload, dérives, économies potentielles — tout est expliqué en €/an et en kWh/m²/DJU.

**Différenciation** : carpet plot 24h × 365j, signature énergétique 3P/4P/5P, CUSUM ISO 50001, anomalies contextuelles ML (LOF + IsolationForest + SHAP), forecasting — niveau Tier 2 différenciant vs concurrents.

### 4.3 Conformité — Régulations comme opportunités

**Rôle** : Décret Tertiaire, BACS, APER, Audit SMÉ, OPERAT.

**Promesse Sol** : la conformité devient une trajectoire claire avec étapes, échéances, scénarios. Pas un tableau d'obligations à cocher — un récit de progression.

**Différenciation** : trajectoire DT versionnée, scoring engine RegOps canonique, simulation mutualisation 2030 (-40 %), calculs déterministes sourcés Décret n°2019-771.

### 4.4 Bill Intelligence — Shadow billing transparent

**Rôle** : audit factures, détection anomalies, contestations, récupération.

**Promesse Sol** : chaque ligne de facture est challengeable. TURPE 7, ATRD, accises, CTA, TVA — le moteur shadow v4.2 compare aux barèmes en vigueur et explique les écarts.

**Différenciation** : récupération automatique, contestations suivies, copy technique explicite avec sources réglementaires — crédibilité B2B forte.

### 4.5 Achat Énergie — Stratégie post-ARENH

**Rôle** : scénarios d'achat, échéances contrats, assistant achat, hedging.

**Promesse Sol** : votre stratégie d'achat est anticipée. Le radar contrats vous prévient, les scénarios sont chiffrés, le marché EPEX est contextualisé.

**Différenciation** : 30 fournisseurs CRE-validés, wizard scénarios, intégration prix EPEX + tendance, post-ARENH/VNU contexte explicite.

### 4.6 Flex Intelligence — Effacement comme revenu

**Rôle** : éligibilité NEBCO, Flex Score, bridge aggregateurs.

**Promesse Sol** : votre patrimoine peut générer des revenus de flexibilité. PROMEOS identifie l'éligibilité, calcule le score, recommande le partenaire (Orus Energy, autres).

**Différenciation** : seul produit qui combine diagnostic flexibilité monétisée + bridge aggregateur sans conflit d'intérêt fournisseur.

### 4.7 Cockpit — Briefing exécutif et opérationnel

**Rôle** : vue COMEX (synthèse portefeuille pour direction) + vue Exploitation (action quotidienne).

**Promesse Sol** : aucun écran d'accueil mort. Chaque jour, le cockpit dit ce qui mérite attention : action urgente, dérive détectée, échéance proche, fenêtre marché, bonne nouvelle.

**Différenciation** : briefing éditorial vivant qui se réécrit chaque jour selon les événements réels du patrimoine.

---

## 5. La grammaire éditoriale Sol

Tout écran Sol respecte une grammaire invariante :

```
[KICKER]                        ← contexte (semaine 17 · patrimoine)
TITRE NARRATIF                  ← Fraunces, voix produit
Narrative 2-3 lignes            ← intro qui raconte
sourcée et chiffrée

[KPI 1] [KPI 2] [KPI 3]         ← 3 KPIs max, avec tooltip ?
   sourcés                          et footer source

CETTE SEMAINE CHEZ VOUS         ← week-cards sémantiques
[À regarder] [À faire] [Bonne nouvelle]

CHARTS / TABLES / DRILL-DOWN    ← profondeur accessible
                                   à la demande

[FOOTER : SOURCE · CONFIANCE · MIS À JOUR]
```

**Règles** :

- **Kicker** : breadcrumb contextualisé, pas un fil d'Ariane technique. Ex : "COCKPIT · SEMAINE 17 · PATRIMOINE TOUS LES SITES — 5 SITES" (et non "Home > Cockpit > Vue exécutive").
- **Titre narratif** : voix Fraunces, ton journal. Ex : "Bonjour — voici votre semaine" ou "Votre patrimoine — sites, contrats et conformité".
- **Narrative** : 2-3 lignes maximum qui racontent ce qui se passe. Mentionne les chiffres importants. Cite les sources de calcul.
- **KPIs** : 3 maximum. Chaque KPI a un tooltip "?" qui définit la mesure et la source. Footer source visible (RegOps, ADEME, EPEX, Enedis).
- **Week-cards** : 3 cards sémantiques typées (À regarder / À faire / Bonne nouvelle / Dérive détectée). Si pas d'action, fallback contextualisé (jamais "Aucune action" pleine largeur).
- **Charts / tables** : accessibles mais pas dominants. Le récit prime, les graphiques illustrent.
- **Footer** : source + niveau de confiance + timestamp dernière mise à jour. Crédibilité B2B.

**Triptyque typographique inviolable** :

- **Fraunces** : titres éditoriaux (display)
- **DM Sans** : corps de texte, lecture longue (body) — formes géométriques douces, ouvertures généreuses, tempérament journal supérieur à Inter
- **JetBrains Mono** : kickers techniques, footers sources, identifiants, KPIs tabular-nums (mono) — supériorité tabular-nums vs IBM Plex Mono pour densité KPI CFO

**Palette journal** : tons crème/brun chaleureux. Active state distinct. Aucun ton corporate froid.

---

## 6. Anti-patterns explicites

Toute PR ou décision produit qui contient un de ces anti-patterns doit être rejetée ou corrigée.

### 6.1 Anti-patterns visuels

- Page qui commence par un tableau ou une grille de KPIs sans préambule
- Card "Aucune action" pleine largeur qui prend 600 px de hauteur
- Notification / message simple qui occupe toute la largeur du panel pour 1 ligne d'info
- Empty state "0 résultats" sans contextualisation
- Écran "N/A 0 kWh chargement" qui reste visible en cas d'absence de data
- Plus de 200 px de hauteur sans information utile
- Couleurs corporate froides (bleu pétrole, gris ardoise) qui rompent la palette journal
- Mélange typographique en dehors du triptyque Fraunces/DM Sans/JetBrains Mono

### 6.2 Anti-patterns navigation

- Menus à 4 niveaux ou plus
- Sous-pages cachées accessibles uniquement par URL directe
- Chemins multiples vers la même information sans hiérarchie claire
- Item de nav qui mène à une page vide ou en chantier
- Item de nav redondant entre 2 modules sans raison
- Routes `-legacy` maintenues sans plan de désactivation explicite

### 6.3 Anti-patterns copy

- Acronymes bruts dans les titres ("DT", "BACS", "TURPE") sans transformation en récit
- Copy qui suppose la connaissance préalable des notions énergétiques
- Tooltip qui répète l'acronyme sans le définir ("DT : Décret Tertiaire" sans expliquer ce qu'il impose)
- Phrases techniques non sourcées
- Mention de chiffres sans unité explicite
- Voix corporate impersonnelle ("La solution permet de...")

### 6.4 Anti-patterns produit

- Feature ajoutée pour "faire le total" sans impact fort
- Module qui ne tiendrait pas debout standalone
- Sous-module redondant avec un autre
- KPI sans définition, sans source, sans formule
- KPI dont la valeur diffère entre 2 écrans pour la même mesure
- Page qui ne change jamais entre 2 jours
- Briefing qui n'oriente pas l'utilisateur vers une action ou une observation pertinente
- Onboarding qui requiert lecture de documentation ou consultant

### 6.5 Anti-patterns architecture

- Logique métier dans le frontend (calculs, scoring, formules)
- Source de vérité multiple pour la même mesure (ex : "total MWh annuel" calculé différemment dans 3 écrans)
- Backend réactif uniquement (qui attend que le frontend demande)
- Absence d'instrumentation des événements produit pertinents
- Tests qui valident le rendu mais pas la cohérence métier transversale

---

## 7. Tests doctrinaux

Pour valider qu'une feature, écran ou décision respecte la doctrine, 8 tests opérationnels.

### Test 1 — Le test des 3 secondes (principe 5)

Screenshot d'un écran Sol montré 3 secondes à un utilisateur. L'utilisateur doit pouvoir résumer immédiatement l'état du patrimoine ou de la fonctionnalité.

### Test 2 — Le test du dirigeant non-sachant (principes 1, 8, 10, 12)

Un dirigeant de PME ou un DAF non-spécialiste énergie ouvre PROMEOS pour la première fois. Il doit comprendre l'essentiel et savoir quoi faire en 3 minutes max sans aide externe.

### Test 3 — Le test du grand écart (principe 3)

La même page Sol est consultée par un utilisateur ETI tertiaire 5 sites et par un dirigeant industriel agroalim 200 sites. Aucun des deux n'a l'impression que le produit "n'est pas pour lui".

### Test 4 — Le test de la densité (principe 4)

Sur une page Sol, dans n'importe quel état du patrimoine, vérifier qu'il n'y a pas plus de 200 px de hauteur sans information utile.

### Test 5 — Le test du standalone (principe 9)

Si on extrayait le module concerné de PROMEOS et qu'on le vendait seul, suffirait-il à payer un abonnement B2B ? Si oui, aligné. Si non, à renforcer.

### Test 6 — Le test du jour J vs J+1 (principe 7)

Comparer 2 captures d'écran d'une même page à 24 h d'intervalle. Au moins 1 card, 1 KPI ou 1 signal doit avoir changé d'état, de priorité ou de contenu.

### Test 7 — Le test de la transformation (principe 10)

Lire la phrase principale d'une page. Un non-sachant la comprend-il sans glossaire externe ? Si oui, transformation réussie. Si non, l'acronyme reste à transformer en récit.

### Test 8 — Le test de l'emplacement (principe 11)

Demander à un utilisateur de trouver une feature en moins de 2 clics depuis n'importe quelle page sans recherche. Si réussi, emplacement correct. Sinon, à repositionner.

---

## 8. Stack technique au service de la doctrine

La doctrine guide les choix techniques, pas l'inverse.

### 8.1 Frontend

- **Framework** : React 18 + Vite + Tailwind v4
- **Charts** : Recharts (intégrable narrativement)
- **Tests** : Vitest (TDD when applicable)
- **Règle d'or** : zéro logique métier dans le frontend. Aucun calcul de score, aucun calcul de trajectoire, aucun calcul d'intensité. Tout vient d'un endpoint backend dédié.
- **Conséquence doctrinale** : si une page Sol affiche un nombre, ce nombre vient d'une seule source backend. Aucune divergence possible entre écrans.

### 8.2 Backend

- **Framework** : FastAPI + SQLAlchemy + SQLite (PostgreSQL-ready)
- **Tests** : pytest avec source-guards anti-régression
- **Source de vérité unique** : `RegAssessment.compliance_score` pour la conformité, `consumption_unified_service` pour les agrégations énergétiques, `naf_resolver` pour la normalisation NAF.
- **Conséquence doctrinale** : un seul endpoint par mesure. Pas de "version simplifiée" ni de "version rapide". Une seule version.

### 8.3 Constantes inviolables

| Donnée                                   | Valeur                                       | Source                     |
| ---------------------------------------- | -------------------------------------------- | -------------------------- |
| CO₂ électricité                          | 0,052 kgCO₂/kWh                              | ADEME Base Empreinte V23.6 |
| CO₂ gaz                                  | 0,227 kgCO₂/kWh                              | ADEME Base Empreinte V23.6 |
| Coefficient énergie primaire électricité | 1,9                                          | depuis janvier 2026        |
| Prix fallback                            | 0,068 €/kWh                                  | référentiel PROMEOS        |
| Accise élec T1 (fév 2026+)               | 30,85 €/MWh                                  | JORFTEXT000053407616       |
| Accise élec T2 (fév 2026+)               | 26,58 €/MWh                                  | JORFTEXT000053407616       |
| Accise gaz (fév 2026+)                   | 10,73 €/MWh                                  | JORFTEXT000053407616       |
| DT jalons                                | -40 % / 2030, -50 % / 2040, -60 % / 2050     | Décret n°2019-771          |
| DT pénalité                              | 7 500 € (3 750 € si à risque)                | Décret n°2019-771          |
| RegOps poids audit applicable            | DT 39 % / BACS 28 % / APER 17 % / AUDIT 16 % | RegOps canonique           |
| RegOps poids audit non-applicable        | DT 45 % / BACS 30 % / APER 25 %              | RegOps canonique           |
| NEBCO seuil                              | 100 kW par pas de pilotage                   | CRE NEBCO                  |
| OID office benchmark                     | ~146 kWhEF/m²/an                             | ADEME ODP 2024             |
| Audit SMÉ deadline                       | 11/10/2026                                   | Réglementation européenne  |

**Anti-pattern doctrinal** : confondre 0,0569 (TURPE 7 HPH €/kWh) avec un facteur CO₂. L'erreur est interdite — elle révèle un manque de discipline référentielle.

---

## 9. Roadmap doctrine — où en sommes-nous

### 9.1 Acquis (Sprint 1 et antérieur)

- Grammaire éditoriale Sol sur 8 pages refondues : Cockpit, Patrimoine, Conformité, Diagnostic Conso, Monitoring, Bill-Intel, Achat, Renouvellements
- Sources citées (ADEME, RegOps, TURPE 7, EPEX) présentes dans les pages refondues
- Densité éditoriale partielle (week-cards "Cette semaine chez vous" sur les pages refondues)
- A11y hardening (Sprint 1 Vague A) : focus rings, keyboard nav, skip link, WCAG contrast
- Features navigation Sol (Sprint 1 Vague B) : Pins, Recents, Mobile Drawer
- Tracker instrumentation (Sprint 1 Vague A) : événements navigation prêts pour analyse adoption
- Permissions filter SolPanel + bridge PERMISSION_KEY_MAP

### 9.2 Chantiers en cours ou backlog Sprint 2

- Câblage 14 pages Sol non encore actives (Anomalies, Contrats, Diagnostic variant, EFA, KB Explorer, RegOps, Renouvellements, Segmentation, Site360, UsagesHoraires, Usages, Watchers, Conformité Tertiaire, Compliance Pipeline)
- Polish vision Sol sur les 8 pages déjà visibles (empty states densifiés, narrative cohérence)
- Audit perf 138 req/page (×3,8 vs main, à comprendre avant merge)
- Test du dirigeant non-sachant (test 2 doctrinal) sur Sprint 1

### 9.3 Chantiers structurels horizon 6-12 mois

**Chantier α — Moteur d'événements proactif** (principe 6 et 7)

Backend qui détecte, priorise et pousse les événements pertinents dans les week-cards et notifications. Sans ce moteur, le principe "le produit pousse, ne tire pas" reste partiel.

- Détection automatique : anomalies, dérives baseline, échéances réglementaires, fenêtres marché EPEX, contestations facture
- Priorisation par impact (€, criticité, urgence)
- Distribution dans les week-cards des pages concernées
- Notifications hors-app (email digest, SMS critique, webhook Teams/Slack)

**Chantier β — Multi-archetype dynamique** (principe 3 et 12)

Adaptation des narratives, KPIs, benchmarks et vocabulaire selon le profil patrimoine connecté.

- Narrative générée par profil (tertiaire / industriel / hôtelier / collectivité / mono-site)
- KPIs prioritaires variables (DT critique tertiaire, Flex critique industriel, etc.)
- Benchmarks adaptés (ADEME bureau ≠ ADEME industrie ≠ collectivité)
- Vocabulaire ajusté selon rôle utilisateur (DAF parle € HT, opérateur parle kWh, dirigeant parle ROI)

**Chantier γ — Apprentissage user via tracker** (principe 2 et 6)

Personnalisation progressive de la nav et des suggestions selon usage observé.

- Pins suggérés selon routes consultées fréquemment
- Raccourcis dynamiques selon cycle d'usage hebdomadaire
- Ordering smart des sections selon priorité observée par utilisateur
- Onboarding guidé qui s'efface au fur et à mesure que l'utilisateur s'approprie l'app

**Chantier δ — Transformation complexité→simplicité systématique** (principe 10)

Audit de toutes les pages Sol pour transformer les acronymes bruts en récits. Reformulation systématique.

- Inventaire de tous les acronymes énergétiques exposés
- Reformulation en récit pour chaque acronyme
- Glossaire accessible mais invisible par défaut
- Passes de "plain language review" périodiques

**Chantier ε — Réseau de connecteurs Enedis/GRDF/SGE** (rigueur infrastructure FR)

Implémentation réelle des intégrations DataConnect + SGE SOAP + GRDF ADICT (aujourd'hui largement stubbées).

- Module `backend/enedis/` complet
- OAuth2 DataConnect + lifecycle consentement
- Client API v5 + catalogue erreurs + parsers R6X
- PHOTO file pipeline (mid-mai 2026)

---

## 10. Positionnement face aux concurrents

| Axe                                           | Advizeo                 | Deepki               | Citron                 | PROMEOS Sol                      |
| --------------------------------------------- | ----------------------- | -------------------- | ---------------------- | -------------------------------- |
| Storytelling éditorial                        | Faible (dashboard)      | Moyen (rapports ESG) | Faible (technique)     | **Fort (briefing journal)**      |
| Non-sachant servi                             | Non (consultant requis) | Partiel              | Non                    | **Oui (cible primaire)**         |
| Bill intelligence intégrée                    | Non                     | Non                  | Non                    | **Oui (shadow v4.2)**            |
| Purchasing intégré                            | Partiel                 | Non                  | Non                    | **Oui (post-ARENH)**             |
| Multi-archetype                               | Tertiaire focus         | Tertiaire / ESG      | Tertiaire / industriel | **Tous archetypes**              |
| Self-serve                                    | 14 semaines onboarding  | Variable             | Variable               | **Oui**                          |
| Intégrations FR (Enedis/SGE/GRDF)             | Variable                | Faible               | Bon                    | **Cible : excellent**            |
| Conformité française (DT/BACS/APER/Audit SMÉ) | Bon                     | Bon                  | Bon                    | **Excellent (RegOps canonique)** |
| Flex Intelligence monetisable                 | Non                     | Non                  | Non                    | **Oui (NEBCO + bridge)**         |

**Argument commercial PROMEOS Sol** : le seul produit français qui combine bill + conformité + achat + flex dans une UX éditoriale pour non-sachants, avec rigueur des sources B2B et infrastructure FR native.

---

## 11. Gouvernance de cette doctrine

### 11.1 Versionnage

Cette doctrine est versionnée. Tout enrichissement, modification ou suppression d'un principe donne lieu à une nouvelle version (1.1, 1.2, 2.0).

- **Patch (1.0 → 1.0.1)** : précision rédactionnelle, exemple ajouté, anti-pattern complété.
- **Minor (1.0 → 1.1)** : nouveau principe ajouté, nouveau test doctrinal, nouvelle section.
- **Major (1.x → 2.0)** : modification de la vision en un paragraphe, suppression ou refonte d'un principe existant.

Chaque version est commitée dans le repo avec un message explicite : `docs(doctrine): v1.1 — add principe 13 X`.

### 11.2 Qui peut modifier

- **Vision et 12 principes** : Amine (founder, product lead) uniquement. Autres contributeurs proposent, Amine arbitre.
- **Anti-patterns** : tout contributeur peut proposer, validation Amine requise.
- **Tests doctrinaux** : tout contributeur peut proposer, validation Amine requise.
- **Stack technique et constantes** : Amine + Staff Engineer.

### 11.3 Référence dans les PR

Toute pull request significative doit pouvoir être justifiée vis-à-vis de la doctrine.

Format suggéré dans le corps de PR :

```markdown
## Doctrine compliance

- Principes respectés : 1, 4, 8, 10
- Principes potentiellement en tension : 7 (le produit ne pousse pas encore ce contenu, à voir Sprint X)
- Anti-patterns évités : "card vide pleine largeur", "acronyme brut en titre"
- Tests doctrinaux validés : test 1 (3 secondes), test 4 (densité)
```

### 11.4 Revue périodique

La doctrine est revue tous les trimestres minimum. Objectifs :

- Aligner la doctrine avec l'évolution réelle du produit
- Détecter les principes qui ne sont plus servis et identifier les chantiers nécessaires
- Détecter les nouveaux principes émergents qui mériteraient inscription
- Mesurer la qualité de l'application en interne (revue PR vs doctrine, tests doctrinaux passés/échoués)

---

## 12. Conclusion — la doctrine en une phrase

> PROMEOS Sol est un OS énergétique vivant qui transforme la complexité en simplicité, qui pousse les bons signaux au bon moment, et qui rend l'énergie B2B compréhensible par tous — non-sachants d'abord, sachants servis également.

Toute décision produit qui ne sert pas cette phrase n'a pas sa place dans PROMEOS Sol.

---

**Doctrine v1.0 — 2026-04-26**
**Statut** : socle. À documenter dans `docs/vision/promeos_sol_doctrine.md` et à référencer dans toute décision produit future.
