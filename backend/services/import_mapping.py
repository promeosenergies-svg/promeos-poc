"""
PROMEOS - Import Mapping (Patrimoine WORLD CLASS)
FR/EN column synonym resolution for CSV/Excel import.
Maps user-provided headers to canonical column names used by the staging pipeline.
"""
from typing import Dict, List, Optional, Tuple

# ========================================
# Canonical columns (staging pipeline)
# ========================================

CANONICAL_COLUMNS = {
    "nom", "adresse", "code_postal", "ville", "surface_m2", "type",
    "naf_code", "siret", "numero_serie", "meter_id", "type_compteur",
    "puissance_kw", "region", "nombre_employes",
    # Contract columns
    "fournisseur", "energie", "prix_kwh", "date_debut", "date_fin",
    "preavis_jours", "abonnement_mensuel",
}


# ========================================
# FR/EN synonym map → canonical column
# ========================================

_SYNONYMS: Dict[str, str] = {
    # nom
    "nom": "nom",
    "nom_site": "nom",
    "name": "nom",
    "site_name": "nom",
    "site": "nom",
    "libelle": "nom",
    "designation": "nom",
    "intitule": "nom",

    # adresse
    "adresse": "adresse",
    "address": "adresse",
    "adresse_postale": "adresse",
    "rue": "adresse",
    "street": "adresse",
    "adresse_site": "adresse",
    "addr": "adresse",

    # code_postal
    "code_postal": "code_postal",
    "cp": "code_postal",
    "code postal": "code_postal",
    "postal_code": "code_postal",
    "zip": "code_postal",
    "zipcode": "code_postal",
    "zip_code": "code_postal",
    "code": "code_postal",
    "codepostal": "code_postal",

    # ville
    "ville": "ville",
    "city": "ville",
    "commune": "ville",
    "localite": "ville",
    "town": "ville",

    # region
    "region": "region",
    "departement": "region",
    "dept": "region",

    # surface_m2
    "surface_m2": "surface_m2",
    "surface": "surface_m2",
    "surface m2": "surface_m2",
    "superficie": "surface_m2",
    "area": "surface_m2",
    "area_m2": "surface_m2",
    "m2": "surface_m2",
    "surface_totale": "surface_m2",
    "sup_m2": "surface_m2",

    # type
    "type": "type",
    "type_site": "type",
    "usage": "type",
    "categorie": "type",
    "category": "type",
    "activite": "type",
    "nature": "type",
    "typologie": "type",

    # naf_code
    "naf_code": "naf_code",
    "naf": "naf_code",
    "code_naf": "naf_code",
    "ape": "naf_code",
    "code_ape": "naf_code",

    # siret
    "siret": "siret",
    "n_siret": "siret",
    "no_siret": "siret",
    "numero_siret": "siret",
    "siren": "siret",

    # nombre_employes
    "nombre_employes": "nombre_employes",
    "employes": "nombre_employes",
    "effectif": "nombre_employes",
    "nb_employes": "nombre_employes",
    "employees": "nombre_employes",
    "headcount": "nombre_employes",

    # numero_serie
    "numero_serie": "numero_serie",
    "n_serie": "numero_serie",
    "serial": "numero_serie",
    "serial_number": "numero_serie",
    "num_serie": "numero_serie",
    "no_serie": "numero_serie",
    "numero_compteur": "numero_serie",

    # meter_id (PRM/PDL/PCE)
    "meter_id": "meter_id",
    "prm": "meter_id",
    "pdl": "meter_id",
    "pce": "meter_id",
    "point_de_livraison": "meter_id",
    "point_livraison": "meter_id",
    "pdl_pce": "meter_id",
    "identifiant_compteur": "meter_id",

    # type_compteur
    "type_compteur": "type_compteur",
    "energie": "type_compteur",
    "type_energie": "type_compteur",
    "energy_type": "type_compteur",
    "vecteur": "type_compteur",
    "fluide": "type_compteur",

    # puissance_kw
    "puissance_kw": "puissance_kw",
    "puissance": "puissance_kw",
    "puissance_souscrite": "puissance_kw",
    "kw": "puissance_kw",
    "power_kw": "puissance_kw",
    "puissance_souscrite_kw": "puissance_kw",
    "kva": "puissance_kw",

    # Contract-related synonyms
    "fournisseur": "fournisseur",
    "supplier": "fournisseur",
    "supplier_name": "fournisseur",
    "nom_fournisseur": "fournisseur",
    "prestataire": "fournisseur",

    "prix_kwh": "prix_kwh",
    "prix_eur_kwh": "prix_kwh",
    "prix_unitaire": "prix_kwh",
    "tarif": "prix_kwh",
    "tarif_kwh": "prix_kwh",
    "price": "prix_kwh",
    "unit_price": "prix_kwh",

    "date_debut": "date_debut",
    "debut_contrat": "date_debut",
    "start_date": "date_debut",
    "debut": "date_debut",

    "date_fin": "date_fin",
    "fin_contrat": "date_fin",
    "end_date": "date_fin",
    "echeance": "date_fin",
    "fin": "date_fin",

    "preavis_jours": "preavis_jours",
    "preavis": "preavis_jours",
    "notice_days": "preavis_jours",
    "notice_period": "preavis_jours",

    "abonnement_mensuel": "abonnement_mensuel",
    "abonnement": "abonnement_mensuel",
    "fixed_fee": "abonnement_mensuel",
    "abo_mensuel": "abonnement_mensuel",
}


# ========================================
# Type value normalization
# ========================================

_TYPE_SITE_SYNONYMS: Dict[str, str] = {
    # bureau
    "bureau": "bureau", "bureaux": "bureau", "office": "bureau", "tertiaire": "bureau",
    # commerce
    "commerce": "commerce", "magasin": "magasin", "boutique": "commerce",
    "retail": "commerce", "supermarche": "commerce", "hypermarche": "commerce",
    # entrepot
    "entrepot": "entrepot", "logistique": "entrepot", "warehouse": "entrepot",
    "stockage": "entrepot", "depot": "entrepot",
    # usine
    "usine": "usine", "industrie": "usine", "production": "usine",
    "factory": "usine", "industriel": "usine",
    # hotel
    "hotel": "hotel", "hotellerie": "hotel", "hebergement": "hotel",
    # sante
    "sante": "sante", "hopital": "sante", "clinique": "sante",
    "ehpad": "sante", "medico_social": "sante",
    # enseignement
    "enseignement": "enseignement", "ecole": "enseignement", "lycee": "enseignement",
    "college": "enseignement", "universite": "enseignement", "education": "enseignement",
    # copropriete
    "copropriete": "copropriete", "copro": "copropriete", "syndic": "copropriete",
    "residence": "copropriete", "immeuble": "copropriete",
    # collectivite
    "collectivite": "collectivite", "mairie": "collectivite",
    "administration": "collectivite", "public": "collectivite",
    # logement social
    "logement_social": "logement_social", "hlm": "logement_social",
    "social": "logement_social", "bailleur": "logement_social",
}

_TYPE_COMPTEUR_SYNONYMS: Dict[str, str] = {
    "electricite": "electricite", "elec": "electricite", "electricity": "electricite",
    "electrique": "electricite", "courant": "electricite",
    "gaz": "gaz", "gas": "gaz", "naturel": "gaz",
    "eau": "eau", "water": "eau",
}


# ========================================
# Public API
# ========================================

def normalize_header(raw_header: str) -> Optional[str]:
    """Map a single raw column header to its canonical name.

    Returns None if no match found.
    """
    key = raw_header.strip().lower().replace("-", "_").replace(" ", "_")
    return _SYNONYMS.get(key)


def normalize_headers(raw_headers: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """Map a list of raw CSV/Excel headers to canonical columns.

    Returns:
        (mapping, unmapped) where mapping is {raw_header: canonical_name}
        and unmapped is the list of headers that couldn't be resolved.
    """
    mapping = {}
    unmapped = []
    for h in raw_headers:
        canonical = normalize_header(h)
        if canonical:
            mapping[h] = canonical
        else:
            unmapped.append(h)
    return mapping, unmapped


def normalize_type_site(raw_value: str) -> Optional[str]:
    """Normalize a site type value using FR synonyms."""
    key = raw_value.strip().lower().replace("-", "_").replace(" ", "_")
    return _TYPE_SITE_SYNONYMS.get(key)


def normalize_type_compteur(raw_value: str) -> Optional[str]:
    """Normalize a compteur type value using FR synonyms."""
    key = raw_value.strip().lower().replace("-", "_").replace(" ", "_")
    return _TYPE_COMPTEUR_SYNONYMS.get(key)


def get_mapping_report(raw_headers: List[str]) -> dict:
    """Generate a diagnostic report for header mapping.

    Useful for the PatrimoineWizard to show the user what was recognized.
    """
    mapping, unmapped = normalize_headers(raw_headers)
    canonical_found = set(mapping.values())
    required = {"nom"}
    missing_required = required - canonical_found
    recommended = {"adresse", "code_postal", "ville", "surface_m2", "type"}
    missing_recommended = recommended - canonical_found

    return {
        "mapped": mapping,
        "unmapped": unmapped,
        "canonical_found": sorted(canonical_found),
        "missing_required": sorted(missing_required),
        "missing_recommended": sorted(missing_recommended),
        "coverage_pct": round(len(mapping) / max(len(raw_headers), 1) * 100, 1),
        "is_valid": len(missing_required) == 0,
    }
