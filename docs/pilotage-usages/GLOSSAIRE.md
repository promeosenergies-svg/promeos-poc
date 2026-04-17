# GLOSSAIRE doctrine — Pilotage des usages

> **Rôle** : source unique de vocabulaire pour le module **Pilotage des usages** de PROMEOS.
> **Audience** : dev, designer, commercial, support — toute personne qui écrit, lit ou relit un label dans le cockpit, un commentaire de code, un pitch ou un mail client.
>
> **Règle de fer** : si un terme est marqué « canonique » ci-dessous, c'est celui-ci qui apparaît dans le front, dans les docs commerciales et dans les sorties d'API orientées utilisateur. Les variantes techniques restent tolérées dans le code interne (noms de fonction, clés JSON techniques), mais jamais dans un wording client-facing.
>
> **Mise à jour** : chaque ajout doit être tracé à une source du dépôt (`backend/services/pilotage/*.py`, `frontend/src/components/pilotage/*.jsx`, `docs/reglementaire/barometre_flex_2026.md`) ou à une source réglementaire externe citée explicitement (RTE, Enedis, CRE, GIMELEC, ADEME, texte NF).

---

## 1. Termes canoniques vs variantes

| Terme canonique | Équivalents acceptés (contexte) | Termes à éviter | Raison doctrine |
|---|---|---|---|
| **Pilotage des usages** | « Pilotage », « Module Pilotage » (navigation, titre section) | Flex, Flexibilité, Effacement, Demand Response, DR | Doctrine Baromètre Flex 2026 : on parle d'usages pilotables (ECS, recharge VE, froid, chauffage), pas d'un « service flex » abstrait. Anti-jargon pour DG/DAF non spécialistes. |
| **Fenêtre favorable probable** | « Créneau favorable », « Fenêtre de décalage » (copy) | Prix négatif, Spot bas, Prix effondré, Heures creuses spot | Doctrine front-end (`radar_prix_negatifs.py` docstring) : client-side on ne spécule pas sur « le prix va être négatif ». On annonce une probabilité de fenêtre exploitable. Anti-anxiogène + non-engageant. |
| **Effacement rémunéré** | « Décalage valorisé », « Effacement valorisé » | NEBCO (client), NEBEF, Décalage brut, DR payant | NEBCO et NEBEF sont des noms de mécanismes RTE (backend). Côté client, on parle du résultat : l'usage est rémunéré quand on l'efface ou le décale. |
| **Potentiel de pilotage** | « Score de pilotage », « Priorité pilotage » | Score flex, Flex score, Note flex, Score NEBEF | Doctrine `portefeuille_scoring.py` l.22 : « classement par potentiel de pilotage (jamais 'classement flex') ». Le S22 mono-site reste « score de potentiel pilotable ». |
| **Puissance pilotable (kW)** | « Puissance mobilisable », « kW pilotables » | Puissance décalable, Puissance effaçable, kW flex | « Pilotable » couvre les deux modes (baisse ET hausse — doctrine NEBCO). « Effaçable » induit un biais baisse-only hérité de NEBEF. |
| **Gain annuel estimé** | « Valorisation annuelle », « Gain annuel Flex Ready® » (carte ROI) | Gain flex, Revenu flex, Cash flex, Bénéfice flex | Cohérent avec la payload `gain_annuel_total_eur` de `compute_roi_flex_ready`. Label CFO-friendly, traçable à une formule documentée. |
| **Flex Ready®** | — (conserver la marque) | Flex-ready, FlexReady, Ready Flex | Marque déposée GIMELEC / Think Smartgrids (2024). Standard **NF EN IEC 62746-4**. Toujours capitalisé avec ® la première occurrence d'une page. |
| **Baromètre Flex 2026** | « Baromètre Flex », « Baro Flex 2026 » (footer, citation courte) | Étude Flex 2026, Rapport flex RTE | Titre officiel publication avril 2026 (RTE / Enedis / GIMELEC / Think Smartgrids / IGNES / ACTEE / IFPEB / SBA). Source primaire du module. |
| **Radar** | « Radar fenêtres favorables » (label carte) | Prédiction, Forecast, Radar prix négatifs (front) | Feature PROMEOS propriétaire. Reste seule (ex. « le Radar détecte… »). Backend peut garder `radar_prix_negatifs.py` comme nom de fichier. |
| **Archétype** | « Archétype NAF », « Archétype d'usage » | Secteur, Type d'activité, Catégorie, Segment | Segment NAF calibré par le Baromètre Flex 2026 (cf. `ARCHETYPE_CALIBRATION_2024`). Ne pas confondre avec « secteur NAF » brut qui regroupe 732 codes. |

---

## 2. Règles de substitution client-side

Règles appliquées à **tout texte visible par un utilisateur externe** (cockpit, bandeau, drawer, modals, emails, exports PDF, slides commerciales). Backend et commentaires techniques peuvent conserver la terminologie d'origine.

| Contexte | Règle | Exemple bon / mauvais |
|---|---|---|
| **Cockpit · cartes Pilotage** | Jamais « NEBCO », « NEBEF » ni « spot négatif ». Utiliser « effacement rémunéré » et « fenêtre favorable probable ». | Bon : « 3 fenêtres favorables probables cette semaine ». Mauvais : « 3 créneaux à prix négatif prédits ». |
| **Bandeau header & toasts** | Pas de sigle technique (NEBCO, FCR, aFRR, MA). Parler de l'effet métier : « décalage rémunéré », « bonus effacement ». | Bon : « Opportunité d'effacement rémunéré détectée ». Mauvais : « Offre MA NEBEF disponible ». |
| **Drawer site & détail** | « Puissance pilotable (kW) » pour un chiffre affiché, « puissance décalable » uniquement dans les tooltips techniques. | Bon : « Puissance pilotable : 120 kW ». Mauvais : « Puissance effaçable : 120 kW ». |
| **Carte ROI Flex Ready®** | Toujours composer avec « Gain annuel Flex Ready® ». Les 3 composantes gardent leurs libellés doctrine : « Évitement pointe », « Décalage NEBCO », « CEE BAT-TH-116 ». | Bon : « Gain annuel Flex Ready® : 4 200 €/an ». Mauvais : « ROI flex : 4 200 € ». |
| **Carte Radar** | Titre : « Radar fenêtres favorables ». Badge : « Anticipation J+7 ». Jamais « Radar prix négatifs » côté UI. | Bon : « Radar fenêtres favorables · Anticipation J+7 ». Mauvais : « Radar prix négatifs J+7 ». |
| **Carte Portefeuille** | Titre : « Classement portefeuille ». Sous-titre : « Sites à prioriser par potentiel de pilotage ». Jamais « classement flex ». | Bon : « Sites à prioriser par potentiel de pilotage ». Mauvais : « Top sites flex du portefeuille ». |
| **Pitch commercial & mails** | Ouvrir sur l'usage concret (« décaler l'ECS », « pré-charger le froid »), pas sur le mécanisme (« valoriser via NEBCO »). | Bon : « Décaler la recharge VE entre 11h et 17h → 60 €/MWh de spread récupéré ». Mauvais : « Valoriser via le mécanisme NEBCO 10h-17h ». |
| **Tooltips techniques (InfoTip)** | Peuvent nommer le mécanisme source pour traçabilité (ex. « kW décalable × ~200 h/an × 60 €/MWh spread »), sans sigle obscur hors contexte. | Bon : « Standard NF EN IEC 62746-4 » (tooltip badge Flex Ready®). Mauvais : « RFC DSM-062746 » (sigle non public). |
| **Niveau de confiance** | Toujours un libellé parmi { `indicative`, `haute`, `réservée` }. Ne pas inventer. | Bon : « confiance indicative ». Mauvais : « précision ±5% ». |
| **Unités & formats** | Euros : `fr-FR` sans décimales par défaut (`fmtEuro`). kW/MWh en chiffres arabes, unité collée sans espace insécable superflu. Probabilité en % entier. | Bon : « 4 200 € · 87 % · 120 kW ». Mauvais : « EUR 4200.00 · 0.87 · 120kW ». |

---

## 3. Acronymes techniques (référence)

Tableau pour les développeurs, analystes et audit. **Ne pas utiliser ces acronymes tels quels côté client** sauf mention explicite « conservé » ci-dessous.

| Acronyme | Libellé | Sens métier | Source officielle |
|---|---|---|---|
| **NEBCO** | Notifications d'Échanges de Blocs de Consommation | Mécanisme RTE actif depuis 1/09/2025. Permet de valoriser des décalages (baisse ET hausse) de consommation. Remplace NEBEF. | RTE / Règles NEBCO 2025 ; Baromètre Flex 2026 |
| **NEBEF** | Notifications d'Échanges de Blocs d'Effacement | Ancien mécanisme (2013-2025) : valorisation d'effacements uniquement. Remplacé par NEBCO au 1/09/2025. Reste cité dans l'historique. | RTE / Règles NEBEF (legacy) |
| **TURPE 7** | Tarif d'Utilisation des Réseaux Publics d'Électricité v7 | Grille tarifaire Enedis/RTE en vigueur depuis 1/08/2025 (CRE n°2025-78). Introduit les Heures Creuses saisonnalisées en 3 phases (cf. §5). | CRE délibération 2025-78 du 1/08/2025 |
| **HC / HP** | Heures Creuses / Heures Pleines | Plages tarifaires avec prix distincts (HC < HP). TURPE 7 saisonnalise les HC ete/hiver. | CRE / Enedis TURPE 7 |
| **CEE BAT-TH-116** | Fiche CEE « Système de gestion technique du bâtiment » (GTB) | Fiche standardisée de valorisation CEE pour installation GTB / BACS. Forfait retenu MVP PROMEOS : **3,5 €/m²** (fourchette 2-5 €/m² 2025-2026). | Arrêté CEE / fiche BAT-TH-116 |
| **GTB** | Gestion Technique du Bâtiment | Système centralisé de pilotage CVC, éclairage, ECS. Pré-requis Flex Ready®. | GIMELEC / ADEME |
| **BACS** | Building Automation & Control System | Système d'automatisation et contrôle obligatoire en tertiaire (décret tertiaire / décret BACS 2020 amendé 2023). 32 000 installés fin 2025, objectif 100 000 en 2030. | Décret n°2020-887 & modifs |
| **BEMS** | Building Energy Management System | Sur-couche logicielle BACS orientée optimisation énergétique. | ISO 50001 / GIMELEC |
| **HEMS** | Home Energy Management System | Équivalent BEMS côté résidentiel. Interface aval du standard NF EN IEC 62746-4 (norme EN 50491-12-2 S2). | Baromètre Flex 2026 |
| **Flex Ready®** | Marque GIMELEC / Think Smartgrids (2024) | Atteste qu'un site/bâtiment expose les 5 données NF EN IEC 62746-4 (horloge, puissance max, prix, puissance souscrite, empreinte carbone). **Conservé client-side**. | NF EN IEC 62746-4 |
| **IEC 62746-4** | NF EN IEC 62746-4 | Norme technique encadrant l'interface entre acteurs marché et GTB/HEMS. Sous-jacent Flex Ready®. | NF / IEC |
| **ADEME** | Agence de la transition écologique | Opérateur public ; source d'études et de méthodologies (dont fiches CEE). | ADEME |
| **ENTSO-E** | European Network of Transmission System Operators for Electricity | Association des GRT européens (dont RTE). Règles de marché européennes. | ENTSO-E |
| **RTE** | Réseau de Transport d'Électricité | GRT (gestionnaire de réseau de transport) France. Opère mécanisme capacité, NEBCO, FCR, aFRR. | RTE |
| **Enedis** | Gestionnaire de réseau de distribution historique | GRD principal France (~95 % PDLs). Publie TURPE et open data. | Enedis |
| **GRD** | Gestionnaire de Réseau de Distribution | Enedis + ELD (entreprises locales de distribution, ~5 % PDLs). | CRE |
| **MA** | Mécanisme d'Ajustement | Mécanisme RTE temps réel pour équilibrer production/conso. Source de revenus pour sites pilotables. | RTE / Règles MA |
| **CDC** | Courbe De Charge | Série temporelle de puissance (pas 10 min ou 30 min). Alimente tout le module. | Enedis SGE M023 / M021 |
| **SF4** | Soutirage Facturé pas 4 (30 min ou 10 min) | Flux Enedis de courbe de charge pour segments C2-C4. | Enedis SGE |
| **TIRU** | Taxe Intérieure sur la Réception d'Électricité | Ancienne appellation de l'accise élec ; à ne plus utiliser, voir « Accise électricité ». | Historique |
| **CTA** | Contribution Tarifaire d'Acheminement | Contribution sociale assise sur la part acheminement TURPE. Concerne élec et gaz. | Arrêté CTA |
| **PPA** | Power Purchase Agreement | Contrat d'approvisionnement long terme (ex. ENR corporate PPA). Hors scope pilotage direct. | — |
| **ARENH** | Accès Régulé à l'Énergie Nucléaire Historique | Mécanisme 2011-2025, supprimé fin 2025. Remplacé par VNU (Versement Nucléaire Universel). | Loi NOME / loi 2023 |
| **VNU** | Versement Nucléaire Universel | Mécanisme post-ARENH (2026+), reversement CRE sur les prix marché. | Loi 2023 nucléaire |

---

## 4. Archétypes canoniques

Les 8 codes alimentent `ARCHETYPE_CALIBRATION_2024` (`backend/services/pilotage/constants.py`). Chaque archétype est calibré par le Baromètre Flex 2026 (RTE / Enedis / GIMELEC, avril 2026), sauf mention.

| Code canonique | Label humain FR | Segment NAF principal | Calibrage source |
|---|---|---|---|
| `BUREAU_STANDARD` | Bureau standard | Section M (activités spécialisées) + 68.2/68.3 (immobilier) + 94 (organisations) | Baromètre Flex 2026 RTE/Enedis — Bureaux |
| `COMMERCE_ALIMENTAIRE` | Commerce alimentaire | 47.11 (hypermarchés, supermarchés, supérettes) + 47.2 (alimentation spécialisée) | Baromètre Flex 2026 RTE/Enedis — Commerces alimentaires |
| `COMMERCE_SPECIALISE` | Commerce spécialisé | 47.3 à 47.9 hors 47.11/47.2 (équipement, textile, sport, etc.) | Baromètre Flex 2026 RTE/Enedis — Commerces non alimentaires |
| `LOGISTIQUE_FRIGO` | Logistique frigorifique | 52.10B (entreposage frigorifique) + 52.29 (services auxiliaires de transport) | Baromètre Flex 2026 RTE/Enedis — Logistique frigorifique |
| `ENSEIGNEMENT` | Enseignement | Section P (enseignement, 85.xx) | Baromètre Flex 2026 RTE/Enedis — Enseignement |
| `SANTE` | Santé | Section Q (santé humaine et action sociale, 86-87-88) | Baromètre Flex 2026 RTE/Enedis — Santé |
| `HOTELLERIE` | Hôtellerie | Section I (55.1 hôtels, 55.2 hébergements similaires, 55.3 camping) | Baromètre Flex 2026 RTE/Enedis — Hôtellerie |
| `INDUSTRIE_LEGERE` | Industrie légère | Section C sous-segments non énergivores (10-18, 22, 25-27, 31-32) | Baromètre Flex 2026 **GIMELEC** — Industrie légère (estimation, non publié Enedis) |

**Règles d'usage** :
- En UI, on affiche le label humain FR (« Bureau standard »), jamais le code brut (`BUREAU_STANDARD`) — sauf badge monochrome technique (carte Portefeuille, heatmap).
- Un compteur inconnu du calibrage retombe sur `BUREAU_STANDARD` (fallback `_DEFAULT_ARCHETYPE` dans `roi_flex_ready.py`), signalé par « Archétype : indéterminé » + confiance « indicative ».
- Le resolveur archétype (`usage_detector.detect_archetype`) combine signal NAF, signature hebdomadaire et talon froid ; il ne doit jamais retourner un code hors de cette liste de 8.

---

## 5. Chiffres de référence (ancrages)

Tous les chiffres doivent citer une source et une date d'effet. Tout chiffre affiché en UI sans source est un bug.

| Valeur | Sens | Source | Date d'effet |
|---|---|---|---|
| **513 h** | Heures de prix spot day-ahead négatifs en France sur 2025 (+46 % vs 352 h 2024) | Observatoire CRE T4 2025 + Baromètre Flex 2026 | Année 2025 |
| **708 000 sites** | Sites inscrits NEBCO fin 2025 (×2 en 1 an vs 340 000 fin 2024) | Baromètre Flex 2026 RTE | 31/12/2025 |
| **NEBCO actif depuis 1/09/2025** | Nouveau mécanisme remplaçant NEBEF ; valorisation des décalages (baisse ET hausse) | Règles NEBCO RTE + Baromètre Flex 2026 | 01/09/2025 |
| **32 000 BACS installés fin 2025** | Objectif 100 000 en 2030 non tenu (rythme actuel → 2040) | Baromètre Flex 2026 ACTEE/SBA | 31/12/2025 |
| **Spread pointe 120 €/MWh** | Écart moyen plage pointe vs plage creuse (hypothèse MVP `SPREAD_POINTE_EUR_MWH`) | Baromètre Flex 2026 + Bulletin marchés gros CRE T4 2025 | Hypothèse 2025-2026 |
| **Spread moyen fenêtre favorable 60 €/MWh** | Écart moyen sur les ~200 h/an de fenêtres favorables (hypothèse MVP `SPREAD_MOYEN_EUR_MWH`) | Baromètre Flex 2026 + Observatoire CRE | Hypothèse 2025-2026 |
| **200 h/an** | Fenêtres annuelles favorables au décalage NEBCO (surplus PV + prix négatifs marginaux + creux TURPE 7) — hypothèse MVP `HEURES_FENETRES_FAVORABLES_AN` | Baromètre Flex 2026 + CRE T4 2025 | Hypothèse 2025-2026 |
| **200 jours/an** | Jours ouvrés effectifs pour activation effacement pointe (hypothèse `JOURS_EFFACEMENT_PAR_AN`) | Hypothèse conservatrice MVP (hors week-ends, fériés, pannes GTB) | Hypothèse |
| **Fiche CEE BAT-TH-116 : 3,5 €/m²** | Forfait valorisation GTB/BACS retenu (fourchette observée 2-5 €/m²) | Arrêté CEE / fiche BAT-TH-116 | Moyenne 2025-2026 |
| **+111 %** | Écart prix pointe 18h-21h vs plage 10h-18h en 2025 (vs +77 % en 2024) | Baromètre Flex 2026 | Année 2025 |
| **3 TWh EnR écrêtés 2025** | Volume EnR écrêté (vs 1,7 TWh 2024) | Baromètre Flex 2026 RTE | Année 2025 |
| **+5,9 GW PV 2025** | Nouveau PV installé France 2025 | Baromètre Flex 2026 | Année 2025 |
| **400 MW Tempo hiver** | Baisse agrégée 30-40 % sur 1,2 M clients Tempo jours rouges | Baromètre Flex 2026 | Hiver 2024-2025 |

**TURPE 7 Phases (HC saisonnalisées Enedis)** :

| Phase | Période de déploiement | Périmètre | HC | Source |
|---|---|---|---|---|
| **Phase 1** | nov 2025 → mai 2026 | 5,2 M clients résidentiels | HC identiques été/hiver | Baromètre Flex 2026 Enedis |
| **Phase 2** | déc 2026 → nov 2027 | 22,8 M clients résidentiels + pro ≤ 36 kVA | HC saisonnalisées été/hiver | Baromètre Flex 2026 Enedis |
| **Phase 3** | juin 2027 → août 2028 | 550 k BT > 36 kVA + HTA | HC saisonnalisées été/hiver | Baromètre Flex 2026 Enedis |

**Créneaux HC TURPE 7 saisonnalisés** (cf. `HC_TURPE7_FAVORABLE` / `HC_TURPE7_EXCLURE` dans `constants.py`) :

| Saison | À favoriser (HC) | À exclure (HP) |
|---|---|---|
| Basse (été, 1/04 → 31/10) | 2h-6h + 11h-17h (heures solaires, surplus PV) | 7h-11h + 18h-23h (montée matin / pic soir) |
| Haute (hiver, 1/11 → 31/03) | 2h-6h + 21h-24h (creux nocturnes) | 7h-11h + 17h-21h (pointe matin + pic soir) |

---

## 6. Ressources

**Sources doctrine PROMEOS** :
- [Baromètre Flex 2026 (doctrine primaire)](../reglementaire/barometre_flex_2026.md)
- [Cartographie réglementaire 2026 Q1](../reglementaire/cartographie_reglementaire_2026Q1.md)
- [Calendrier échéances réglementaires](../reglementaire/calendrier_echeances.md)
- [Innovation Roadmap Pilotage](./INNOVATION_ROADMAP.md)

**Code source (référence canonique des codes & formules)** :
- `backend/services/pilotage/constants.py` — codes archétypes + calibrage Baromètre 2024 + créneaux TURPE 7
- `backend/services/pilotage/roi_flex_ready.py` — formule gain annuel Flex Ready® (3 composantes)
- `backend/services/pilotage/radar_prix_negatifs.py` — détection fenêtres favorables probables J+7
- `backend/services/pilotage/portefeuille_scoring.py` — classement portefeuille par potentiel de pilotage
- `backend/services/pilotage/score_potential.py` — scoring mono-site S22
- `frontend/src/components/pilotage/RadarPrixNegatifsCard.jsx` — carte Radar (wording client)
- `frontend/src/components/pilotage/RoiFlexReadyCard.jsx` — carte ROI Flex Ready® (wording client)
- `frontend/src/components/pilotage/PortefeuilleScoringCard.jsx` — carte Portefeuille (wording client)

**Sources externes officielles** :
- RTE — Bilan électrique 2025, Règles NEBCO, Règles MA.
- Enedis — Open Data BACS, TURPE 7 déploiement phases, SGE / SF4.
- GIMELEC / Think Smartgrids — marque Flex Ready®, norme NF EN IEC 62746-4.
- CRE — Observatoire T4 2025, Bulletin marchés de gros T4 2025, délibérations 2025-78 (TURPE 7) et 2025-122 (modulation négative).
- ADEME — Fiches CEE standardisées (BAT-TH-116).

---

**Contrat de maintenance** : toute PR qui introduit ou modifie un label Pilotage visible côté client doit mettre à jour ce document dans le même commit. Un label orphelin (= sans entrée dans ce glossaire) est un motif de refus de merge.
