"""
PROMEOS - Module pilotage des usages.

Voir README.md pour l'onboarding dev complet (archi, responsabilites, depend-
ances, glossaire doctrine) et `docs/pilotage-usages/INNOVATION_ROADMAP.md`
pour la roadmap produit.

Sous-modules :
    - constants.py            : 3 referentiels calibrage Barometre Flex 2026
                                (ARCHETYPE_RULES + ARCHETYPE_CALIBRATION_2024
                                + HC_TURPE7_FAVORABLE/EXCLURE + mappings seed)
    - connectors/             : connecteurs data externes (ENTSO-E day-ahead,
                                RTE Tempo OAuth2, ADEME emission factors)
    - flex_ready.py           : 5 signaux standardises NF EN IEC 62746-4
                                (horloge + puissance max + prix + puissance
                                souscrite + empreinte carbone)
    - score_potential.py      : score 0-100 potentiel pilotable mono-site
                                (socle S22 avant V1)
    - usage_detector.py       : detection des usages flexibles par archetype
    - window_detector.py      : classification slots J+7 en FAVORABLE /
                                SENSIBLE / NEUTRE avec indice TURPE 7 HC
                                saisonnalise
    - radar_prix_negatifs.py  : prediction heuristique fenetres prix negatifs
                                J+7 (V1 Piste 1 INNOVATION_ROADMAP)
    - roi_flex_ready.py       : business case chiffre EUR/an (V1 Piste 2 :
                                evitement pointe + effacement + CEE BAT-TH-116)
    - portefeuille_scoring.py : classement multi-sites par potentiel pilotable
                                + heatmap par archetype (V1 Piste 3)

Source doctrine primaire : Barometre Flex 2026 (RTE / Enedis / GIMELEC / Think
Smartgrids / IGNES / ACTEE / IFPEB / SBA / AICN, avril 2026). Voir
`docs/reglementaire/barometre_flex_2026.md`.

Ce __init__.py reste sans imports pour eviter les cycles au chargement (le
module compliance/scoring charge plusieurs services de ce package).
"""
