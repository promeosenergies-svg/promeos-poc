"""
PROMEOS — Briques de calcul facture (refactor V112).

Chaque module expose une fonction pure `compute_<brick>(...)` qui prend en
entrée les données métier et un ParameterStore, et retourne une dict
structurée avec la valeur HT, le taux unitaire, la source d'audit.

Ordre d'appel dans le pipeline (cf. doctrine shadow billing) :
    1. ensure_energy
    2. fourniture
    3. acheminement (TURPE / ATRD+ATRT+ATS)
    4. CTA
    5. CEE
    6. accise
    7. prestations
    8. TVA (sur base totale HT)
"""

from .cta import compute_cta, CtaResult  # noqa: F401
