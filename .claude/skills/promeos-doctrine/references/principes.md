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

