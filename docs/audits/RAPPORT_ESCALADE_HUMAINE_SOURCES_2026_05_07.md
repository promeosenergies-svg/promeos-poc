# Rapport escalade humaine — Sources réglementaires à figer Phase D-4

**Date** : 2026-05-07
**Branche** : `claude/refonte-sol2`
**Contexte** : Sprint Audit Réglementaire Cardinal (3 agents `regulatory-expert` SDK parallèles) — toutes les sources externes premier rang sont **inaccessibles WebFetch** (403/503/404 systématiques). Cross-check KB `reference_regulatory_landscape_2026_2050.md` + `agent_veille_reglementaire.md` confirme partiellement les données mais ne livre PAS les NOR/JORFTEXT/URLs précises.

⚠️ **Discipline cardinale Pilier 9 ADR-016** respectée : aucun NOR/URL/date inventé. Tout ce qui suit nécessite vérification humaine directe sur navigateur.

---

## Mode d'emploi

Pour chaque ligne :
- **🎯 Cible** : ce qu'on cherche (ex. NOR exact, JORFTEXT, date publication JO)
- **🔗 URL probable** : URL navigateur pour confirmation (à vérifier par toi en navigateur direct)
- **📋 Mots-clés recherche** : si l'URL ne fonctionne pas, mots-clés à rechercher sur Légifrance/CRE/Google
- **🧐 Hypothèse** : ce qu'on suspecte (à confirmer/infirmer)
- **📂 Fichier impacté** : où le résultat doit être reporté

---

## SOURCE 1 — TURPE 7 NOR + JORFTEXT (P0.1 Phase D-2 résiduel)

🎯 **Cible** :
- NOR Légifrance de la délibération CRE n°2025-78 du 13/03/2025
- JORFTEXT de l'arrêté énergie qui ratifie la délibération CRE 2025-78
- Date publication JO réelle (le YAML dit `2025-05-14` Phase D-1, Phase D-2 a maintenu la date d'application 01/02/2025)

🔗 **URLs probables** :
- https://www.cre.fr/documents/deliberations/tarif-dutilisation-des-reseaux-publics-de-distribution-delectricite-turpe-7-hta-bt-1.html
- https://www.legifrance.gouv.fr/search/all?tab_selection=jorf&query=TURPE+2025-78
- https://www.legifrance.gouv.fr/jorf/jo/2025/03 (JO mars 2025)

📋 **Mots-clés** : `"délibération 2025-78" CRE TURPE 7 HTA-BT NOR JO`

🧐 **Hypothèse** : publication JO entre 14/03 et 31/03/2025 (déliberation CRE adoptée 13/03/2025, publiée site CRE 20/03/2025). Date application = **01/02/2025** (mouvement exceptionnel CRE 12/12/2024 — déjà fixé Phase D-2).

📂 **Fichier impacté** : `backend/config/tarifs_reglementaires.yaml` lignes 71-80 (clé `turpe.source` + ajouter `nor` + `url_legifrance` + `jorftext`)

---

## SOURCE 2 — TURPE 7 codes FTA exhaustifs (P0.2 Phase D-2 partiel)

🎯 **Cible** : liste exhaustive codes FTA TURPE 7 avec mapping segment/domaine_tension/nb_postes (PDF délibération 2025-78 annexes tarifaires, 4,29 MB).

Phase D-2 a verrouillé 6 codes medium-confidence : `BTINFCU4`, `BTINFMU4`, `BTSUPCU`, `BTSUPLU`, `HTACU5`, `HTALU5`. Phase D-3 doit confirmer ou élargir.

🔗 **URL probable** :
- https://www.cre.fr/documents/deliberations/tarif-dutilisation-des-reseaux-publics-de-distribution-delectricite-turpe-7-hta-bt-1.html (page CRE — onglet "Annexes" ou pièces jointes PDF)

📋 **Mots-clés** : `"TURPE 7" annexe codes BTINFCU4 BTSUP HTACU5`

🧐 **Hypothèse** : 4 préfixes (BTINF / BTSUP / HTA / HTB) × 3 suffixes durée (CU / MU / LU) × 2 ou 4-5 nb postes = ~12-15 codes canoniques au total.

📂 **Fichier impacté** : `backend/models/enums.py:FtaCode` (élargir l'Enum) + `backend/doctrine/constants.py:CANONICAL_FTA_CODES_TURPE_7` (élargir le tuple)

---

## SOURCE 3 — TURPE 7 BT 18.48 €/mois ou 16.80 €/MWh (P1 résiduel)

🎯 **Cible** : confirmer que `gestion C5 BT TURPE 7 = 18.48 EUR/mois` (cf. `tarifs_reglementaires.yaml:85`) est correct vs hypothèse "16.80 €/MWh" du brief Phase D-3.

🔗 **URL probable** : annexe tarifaire PDF délibération CRE 2025-78 (cf. SOURCE 2)

📋 **Mots-clés** : `"TURPE 7" "C5 BT" gestion abonnement annuel mensuel 18.48 16.80`

🧐 **Hypothèse forte** : confusion brief unité **€/mois** (gestion abonnement) vs **€/MWh** (composante énergie). Évolution TURPE 6 → TURPE 7 = 2.14 → 18.48 €/mois (×8.6) = cohérent refonte gestion TURPE 7. Le 16.80 €/MWh n'apparaît dans aucun YAML.

📂 **Fichier impacté** : `backend/config/tarifs_reglementaires.yaml:85` (commenter avec source officielle)

---

## SOURCE 4 — CTA TURPE fixe 2026 valeur exacte (P0-REG-004)

🎯 **Cible** :
- Taux CTA distribution élec 2026 (YAML actuel : 15.0%)
- Taux CTA transport élec 2026 (YAML actuel : 5.0%)
- **Origine du chiffre 27.04%** mentionné brief Phase D-3 (introuvable YAML)

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/search/all?tab_selection=jorf&query=CTA+27%2F01%2F2026
- https://www.cre.fr/documents/deliberations (rechercher 2026-14)

📋 **Mots-clés** : `"arrêté 27 janvier 2026" CTA contribution tarifaire acheminement TURPE fixe taux %`

🧐 **Hypothèses** :
1. 27.04% pourrait être un draft pré-arrêté (CRE 2026-14 prévoyait peut-être ce taux qui a été révisé à la baisse à 15+5=20%)
2. 27.04% = somme **CTA gaz** distribution + transport (mais YAML stocke 20.80 + 4.71 ≈ 25.5%)
3. 27.04% = chiffre brouillon brief

📂 **Fichier impacté** : `backend/config/tarifs_reglementaires.yaml` lignes ~245-260 (clés `cta.elec` + `cta.elec_transport` + `cta_2021.elec` + `cta_2021.elec_transport`)

---

## SOURCE 5 — JORFTEXT000053407616 attribution élec/gaz (P0-REG-005)

🎯 **Cible** : confirmer si l'arrêté JORFTEXT000053407616 du 27/01/2026 fixe :
- (a) **uniquement les accises gaz** (10.73 EUR/MWh)
- (b) **uniquement les accises électricité** (T1=30.85 / T2=26.58 / HP=5.71 EUR/MWh)
- (c) **les deux** (arrêté annuel d'indexation accises ATU énergie)

🔗 **URL probable** : https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053407616

📋 **Mots-clés** : `"JORFTEXT000053407616" arrêté 27 janvier 2026 accise énergie électricité gaz`

🧐 **Hypothèse forte** : (c) arrêté unique multi-fluides (cohérent pratique annuelle d'indexation).

📂 **Fichier impacté** :
- `backend/config/tarifs_reglementaires.yaml:217` (déjà côté gaz)
- `backend/config/tarifs_reglementaires.yaml` lignes 167-186 (3 sections `accise_elec_2026_t1/t2/hp` — actuellement absent)

---

## SOURCE 6 — TICGN 4 périodes 2026 (P1-REG-004)

🎯 **Cible** : confirmer si LFI 2026 ou arrêté 2026 instaure une **saisonnalité TICGN** (4 périodes hiver/été ou similaire) pour le gaz.

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/loda/id/JORFTEXT000048727128 (LFI 2024 — base TICGN)
- https://www.douane.gouv.fr/dossier/taxes-energetiques (DGDDI page accises gaz)

📋 **Mots-clés** : `TICGN 2026 saisonnière 4 périodes accise gaz`

🧐 **Hypothèse** : soit le brief anticipe une mesure non encore publiée, soit erreur du brief. Le YAML stocke **un taux unique** gaz fév 2026+ (10.73 EUR/MWh) → cohérent doctrine.

📂 **Fichier impacté** : éventuellement `backend/config/tarifs_reglementaires.yaml` clé `accise_gaz` (à reformater en 4 périodes si confirmé).

---

## SOURCE 7 — ATRT8 GRTgaz NOR + délibération CRE (P1-REG-003)

🎯 **Cible** :
- Numéro délibération CRE pour ATRT8 (transport gaz GRTgaz/NaTran/Teréga)
- NOR Légifrance + JORFTEXT
- Date publication JO

🔗 **URLs probables** :
- https://www.cre.fr/documents/deliberations (rechercher "ATRT8")
- https://www.legifrance.gouv.fr/search/all?tab_selection=jorf&query=ATRT8

📋 **Mots-clés** : `ATRT8 GRTgaz NaTran Teréga délibération CRE NOR transport gaz`

🧐 **Hypothèse** : ATRT8 = 8e période tarifaire transport gaz. ATRT7 (2020-2024) suivi par ATRT8 (2025+). YAML cite seulement "CRE ATRT8 2025" sans n° précis.

📂 **Fichier impacté** : `backend/config/tarifs_reglementaires.yaml:473-483` (clé `atrt_gaz` — actuellement source presse SirEnergies)

---

## SOURCE 8 — Décret Tertiaire — pénalité site at-risk 3750€ origine (P1-REG-005)

🎯 **Cible** : confirmer si `DT_PENALTY_AT_RISK_EUR = 3750` (`constants.py:28`) provient :
- (a) d'un texte juridique (décret/circulaire)
- (b) d'un calcul scoring interne PROMEOS (probable : 7500 / 2 = 3750)

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000041565617 (art. L.174-1 CCH)
- https://operat.ademe.fr (FAQ pénalités)

📋 **Mots-clés** : `Décret Tertiaire pénalité 3750 7500 amende administrative L174-1 CCH`

🧐 **Hypothèse forte** : (b) heuristique scoring interne. À renommer `DT_PENALTY_AT_RISK_INTERNAL_SCORING_EUR` ou flagger explicitement.

📂 **Fichier impacté** : `backend/doctrine/constants.py:28` (commentaire ou rename)

---

## SOURCE 9 — OPERAT pénalité 1500€ Circulaire DGEC 2024 (P1-REG-006)

🎯 **Cible** : numéro précis + URL de la "Circulaire DGEC 2024" citée comme source de `OPERAT_PENALTY_EUR = 1500` (`constants.py:35`).

🔗 **URLs probables** :
- https://www.ecologie.gouv.fr/sites/default/files/circulaires (rechercher DGEC 2024)
- https://operat.ademe.fr/Documentation (FAQ ADEME OPERAT)

📋 **Mots-clés** : `circulaire DGEC 2024 OPERAT pénalité 1500 amende non-déclaration`

🧐 **Hypothèse** : la circulaire pourrait ne pas exister ou être confidentielle interne — la valeur 1500 € serait alors pratique consensuelle non sourcée formellement.

📂 **Fichier impacté** : `backend/doctrine/constants.py:35` (commentaire)

---

## SOURCE 10 — BACS décret modificateur 2024/2025 (P1-REG-007/008)

🎯 **Cible** :
- Numéro précis du décret BACS modificateur (post Décret 2020-887 initial) qui abaisse le seuil 290 kW → 70 kW au 01/01/2030
- KB confirme `>70 kW : 01/01/2030 obligation` (cf. `reference_regulatory_landscape_2026_2050.md`) — donc règle existe, source à figer.

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/loda/id/JORFTEXT000042134973 (Décret 2020-887 initial)
- https://www.legifrance.gouv.fr/search/all?tab_selection=jorf&query=BACS+70+kW

📋 **Mots-clés** : `décret BACS 2025 70 kW 290 kW bâtiments tertiaires existants 01/01/2030`

🧐 **Hypothèse** : décret modificateur publié 2024 ou 2025 (Loi industrie verte 23/10/2023 a peut-être déclenché révision).

📂 **Fichier impacté** :
- `backend/doctrine/constants.py:32` (commentaire BACS_PENALTY_EUR + ajout date 01/01/2030)
- Nouvelle constante `BACS_THRESHOLD_KW_EXISTING = 70`
- Nouvelle constante `BACS_DEADLINE_EXISTING = "2030-01-01"`

---

## SOURCE 11 — APER décret application réel (P0-REG-001)

🎯 **Cible** : numéro correct du décret d'application de la **Loi 2023-175 art. 40** (10/03/2023) sur la solarisation des parkings APER.

⚠️ **Le commentaire actuel `constants.py:47-50` cite "Décret 2022-1726" qui est CHRONOLOGIQUEMENT IMPOSSIBLE** (décret antérieur à la loi qu'il prétend appliquer).

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294383 (Loi 2023-175 art. 40)
- https://www.legifrance.gouv.fr/search/all?tab_selection=jorf&query=parking+1500+m%C2%B2+solarisation+APER

📋 **Mots-clés** : `décret application loi APER 2023-175 parking solarisation 1500 m² 10000 m²`

🧐 **Hypothèses** : Décret 2024-1023 OU 2024-1318 (à confirmer). Le décret 2022-1726 (Pacte vert / urbanisme commercial) est probablement une référence pré-loi APER non applicable.

📂 **Fichier impacté** : `backend/doctrine/constants.py:47-50` (corriger commentaire urgent)

---

## SOURCE 12 — APER échéance 01/07/2026 parkings >10000 m² (P0-REG-002)

🎯 **Cible** : confirmer que parkings extérieurs >10 000 m² doivent être solarisés avant **01/07/2026** (échéance imminente, fenêtre 2 mois).

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294383 (Loi APER art. 40 II)

📋 **Mots-clés** : `loi APER échéance 2026 2028 parking 10000 m² 1500 m² calendrier`

🧐 **Hypothèse forte** : 2 échéances distinctes :
- **01/07/2026** : parkings >10 000 m² (gros centres commerciaux, logistique)
- **01/07/2028** : parkings 1500-10 000 m² (PROMEOS cible mid-market)

📂 **Fichier impacté** :
- `backend/doctrine/constants.py:52` (`APER_DEADLINE_DATE = "2028-01-01"` — corriger en `"2028-07-01"`)
- Ajouter `APER_DEADLINE_LARGE_PARKING_DATE = "2026-07-01"` + seuil 10000 m²

---

## SOURCE 13 — Audit SMÉ Décret 2024-1304 (P1-REG-010)

🎯 **Cible** : confirmer existence + numéro exact du Décret 2024-1304 (transposition EED révisée 2023/1791) qui pose les seuils 2.75 GWh / 23.6 GWh + deadline 11/10/2026.

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/search/all?tab_selection=jorf&query=2024-1304+audit+%C3%A9nerg%C3%A9tique
- https://www.ecologie.gouv.fr/audit-energetique-grandes-entreprises

📋 **Mots-clés** : `décret 2024-1304 audit énergétique entreprises 2.75 GWh 23.6 GWh 11 octobre 2026 EED 2023/1791`

🧐 **Hypothèse** : décret existe (KB cohérent avec EED) mais numéro à confirmer (2024-1304 plausible).

📂 **Fichier impacté** : `backend/doctrine/constants.py:65-68` (commentaire AUDIT_SME_*)

---

## SOURCE 14 — NEBCO délibération CRE + RTE règles MA-RE (P0-REG-008)

🎯 **Cible** :
- Numéro délibération CRE NEBCO (probablement 2024-XX ou 2025-XX, publiée Q1-Q2 2025)
- Lien règles RTE MA-RE Section NEBCO
- Date d'application précise (`constants.py` commentaire dit 01/09/2025 — non sourcé)

🔗 **URLs probables** :
- https://www.cre.fr/documents/deliberations (rechercher "NEBCO" ou "engagement baisse consommation")
- https://www.services-rte.com/fr/visualisez-les-donnees-publiees-par-rte (règles mécanisme effacement MA-RE)

📋 **Mots-clés** : `NEBCO notification engagement baisse consommation 100 kW délibération CRE 2025 RTE MA-RE`

🧐 **Hypothèse** : délibération CRE 2025 paramètres effacement / NEBCO. RTE règles MA-RE Section X pour fenêtres horaires (J-1 09:30 + J 22:00).

📂 **Fichier impacté** : `backend/doctrine/constants.py:55-58 + 92-94` (ajouter commentaires source)

---

## SOURCE 15 — L.332-7 quart-heure 01/10/2025 (P0-REG-009)

🎯 **Cible** :
- Article L.332-7 Code énergie version en vigueur au 01/10/2025
- Loi modificatrice qui introduit l'obligation de tarification dynamique au quart d'heure
- Date d'entrée en vigueur précise

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044626773 (Code énergie L.332-7 — version générique)
- https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000023983208/LEGISCTA000023985137 (Section L.332)

📋 **Mots-clés** : `L.332-7 Code énergie tarification dynamique quart heure 01/10/2025 fournisseur électricité`

🧐 **Hypothèses** :
1. Loi APER 2023-175 (10/03/2023) — possible
2. Loi industrie verte 2023-973 (23/10/2023) — possible
3. Loi souveraineté énergétique 2024 — à confirmer
4. Transposition Directive UE 2019/944 art. 11 (offre tarif dynamique fournisseurs >200 000 clients)

📂 **Fichier impacté** :
- `backend/doctrine/constants.py` (créer constantes `L332_7_DATE_APPLICATION` + threshold clients fournisseur)
- `backend/services/consumption_unified_service.py` (impact pas CDC 1/4h Enedis SGE M023 — si confirmé)

---

## SOURCE 16 — VNU Loi 2024-1119 + délibération CRE VNU (P0-REG-010)

🎯 **Cible** :
- Confirmer existence + intitulé exact de la **Loi 2024-1119** du 11/12/2024 (post-ARENH / nouvelle régulation nucléaire)
- Numéro délibération CRE VNU (paramètres seuils prix bas/haut)
- Date application 01/01/2026

🔗 **URLs probables** :
- https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050766XXX (à compléter — JO 11-12/12/2024)
- https://www.cre.fr/documents/deliberations (rechercher "VNU" ou "versement nucléaire")

📋 **Mots-clés** : `loi 2024-1119 versement nucléaire universel post-ARENH 01/01/2026 EDF`

🧐 **Hypothèse** : loi existe (KB confirme `VNU tarif unitaire = 0 pour 2026`). Le mécanisme est actif mais non-facturant en 2026 (seuils prix non franchis).

📂 **Fichier impacté** :
- `backend/doctrine/constants.py:90-94` (créer `VNU_DATE_APPLICATION = "2026-01-01"` + `VNU_PRICE_FLOOR_EUR_PER_MWH` + `VNU_PRICE_CEILING_EUR_PER_MWH` + `VNU_REGULATORY_REFERENCE`)
- Le `POST_ARENH_RATIO_2026_VS_2024 = 1.225` reste une **référence sectorielle** distincte du mécanisme VNU lui-même.

---

## SOURCE 17 — Délibération CRE 2026-33 heures solaires HC (P1-REG-009)

🎯 **Cible** : confirmer existence + numéro exact de la délibération CRE 2026-33 (heures solaires HC TURPE 7).

🔗 **URLs probables** :
- https://www.cre.fr/documents/deliberations (rechercher "2026-033" ou "heures solaires" ou "heures creuses TURPE 7")

📋 **Mots-clés** : `CRE délibération 2026-33 heures solaires creuses TURPE 7 plage 11h 14h saisonnalité été`

🧐 **Hypothèse** : délibération potentielle Q1 2026 (numéro 2026-33 plausible). Plage 11h-14h été serait la nouvelle fenêtre HC saisonnalisée Phase 2 reprog HC TURPE 7.

📂 **Fichier impacté** :
- `backend/config/tarifs_reglementaires.yaml` (clé `turpe.segments` — ajouter sous-clé `heures_solaires` si confirmé)
- Module reprog HC (`V110-HC` Phase 2) — re-calcul nécessaire si confirmé.

---

## Récapitulatif — 17 sources à figer

| # | Source | Priorité | Effort estimé (humain) |
| --- | --- | --- | --- |
| 1 | TURPE 7 NOR + JORFTEXT | P0 | 10 min |
| 2 | TURPE 7 codes FTA exhaustifs (PDF 4 MB) | P0 | 30 min (parsing PDF) |
| 3 | TURPE 7 BT 18.48 vs 16.80 | P1 | 5 min |
| 4 | CTA 27.04% origine | P0 | 10 min |
| 5 | JORFTEXT000053407616 attribution | P0 | 5 min |
| 6 | TICGN saisonnalité 2026 | P1 | 10 min |
| 7 | ATRT8 NOR | P1 | 10 min |
| 8 | DT pénalité 3750€ origine | P1 | 5 min |
| 9 | OPERAT 1500€ Circulaire DGEC | P1 | 10 min |
| 10 | BACS décret modificateur 2024/2025 | P0 | 10 min |
| 11 | **APER décret application réel** (chronologie incohérente) | **P0 BLOQUANT** | 10 min |
| 12 | APER échéance 01/07/2026 (>10000 m²) | P0 | 5 min |
| 13 | Audit SMÉ Décret 2024-1304 | P1 | 5 min |
| 14 | NEBCO délibération CRE | P0 | 15 min |
| 15 | L.332-7 quart-heure | P0 | 15 min |
| 16 | VNU Loi 2024-1119 | P0 | 15 min |
| 17 | CRE 2026-33 heures solaires | P1 | 10 min |

**Total effort humain estimé** : ~3 heures recherche manuelle Légifrance/CRE en navigateur direct.

---

## Action recommandée

1. **Ouvrir un navigateur sur Légifrance.gouv.fr** (le 403 WebFetch est anti-bot, navigateur humain passe).
2. Pour chaque ligne ci-dessus :
   - Tester l'URL probable
   - Si erreur, copier les mots-clés dans le moteur de recherche Légifrance
   - Noter NOR + JORFTEXT + URL + dates
3. **Reporter les résultats** dans un fichier `docs/audits/SOURCES_OFFICIELLES_VERIFIEES_2026_05_DD.md` avec format :

```markdown
## SOURCE 11 — APER décret application
- **Décret confirmé** : Décret 2024-XXXX du JJ/MM/2024
- **NOR** : XXXX2418XXXX
- **JORFTEXT** : JORFTEXT000050XXXXXX
- **URL** : https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050XXXXXX
- **Date publication JO** : YYYY-MM-DD
- **Pénalité** : 20 €/m²/an confirmé
```

4. **Communiquer** ce doc à l'agent (via `/audit-followup`) pour que Phase D-3 hotfix Tier 0 puisse appliquer les corrections en code/YAML.

---

## Sources déjà confirmées via KB (cross-check `reference_regulatory_landscape_2026_2050.md`)

✅ **TURPE 7** : période 2025-2028 (cohérent Phase D-2)
✅ **ATRD 7 GRDF** : 01/07/2024 pour 4 ans (cohérent YAML L411)
✅ **BACS** : 70 kW au 01/01/2030 (à encoder en constante — cf. SOURCE 10)
✅ **VNU** : tarif unitaire = 0 pour 2026 (mécanisme actif, non-facturant)
✅ **Audit SMÉ** : seuils 2.75 / 23.6 GWh confirmés EED révisée

⚠️ **APER décret 2022-1726 incohérent chronologiquement** confirmé par absence de mention dans KB (décret application réel reste à identifier).

---

**Auteur** : Sprint Audit Réglementaire Cardinal — 3 agents `regulatory-expert` SDK parallèles
**Date** : 2026-05-07
**Branche** : `claude/refonte-sol2`
**Statut** : escalade humaine cardinale — toutes sources externes WebFetch bloquées (403/503/404 systématiques)
