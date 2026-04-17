"""
PROMEOS - Module pilotage des usages.

Sous-modules :
    flex_ready      : signaux standardises Flex Ready (R) conformes NF EN IEC 62746-4
    connectors      : connecteurs GTB / marche (ENTSO-E day-ahead, ...)
    window_detector : classification des slots J+7 en FAVORABLE / SENSIBLE /
                      NEUTRE avec indice TURPE 7 HC saisonnalise (S22)

Note: les modules historiques (usage_detector, score_potential) du sprint
S1-S21 sont presents mais volontairement minimalistes dans cette branche.
Garder ce __init__.py minimal pour eviter des imports circulaires au
chargement du package.
"""
