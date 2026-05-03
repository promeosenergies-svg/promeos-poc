"""OperatValeursAbsoluesService — SoT chaîne 4 lookups Cabs 2030 OPERAT.

Sprint C-1 Phase 4 — comble GAP R2 audit Phase B (matrice v1 §5.3).

Chaîne : code_postal → zone → palier altitude → CVCi/USEi → Coeff DJU → Cabs 2030 ajusté.

Sources réglementaires :
- Annexes I+II arrêté 01/08/2025 NOR ATDL2430864A (consolide VA I→V)
  Données structurées :
    backend/config/operat_annexe_i_sous_categories.json (931 KB, 426 sous-cat × 13 zones × 5 paliers)
    backend/config/operat_annexe_ii_coeff_dju.json (10 KB, 13 groupes G1-G13)
- Annexe III arrêté 10/04/2020 NOR LOGL2005904A v2 (07/09/2025) — zones authentifiées 🟢
  Données : backend/config/operat_zones_climatiques.json (101 entités) + resolver
  regops/operat_zones.py.

Confidence : 🟢 zones authentifiées par recoupement direct PDF Légifrance v2 03/05/2026.

Convention : tooltip traçabilité (NOR + URL Légifrance + date) retourné avec chaque
lookup, pour exposition frontend (différenciateur PROMEOS Sol §13 "info fiable").

⚠️ Normalisation noms zones :
- Annexe III (zones officielles) : "Réunion" (avec accent)
- OperatZoneClimatiqueEnum : "Réunion" (cohérent)
- Annexe I JSON (extraction PDF) : "Reunion" (sans accent — encodage extraction)
  → Le service normalise automatiquement avant lookup index.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional


_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"  # backend/config
_ANNEXE_I_FILENAME = "operat_annexe_i_sous_categories.json"
_ANNEXE_II_FILENAME = "operat_annexe_ii_coeff_dju.json"


# ─── Exceptions métier ────────────────────────────────────────────────────────


class OperatNonAssujettiError(Exception):
    """Site hors périmètre OPERAT (COM 975/977/978 ou code postal invalide)."""


class OperatSousCategorieIntrouvableError(Exception):
    """Sous-catégorie non trouvée dans Annexe I."""


# ─── Helpers internes ─────────────────────────────────────────────────────────


@lru_cache(maxsize=4)
def _load_json(filename: str) -> dict:
    """Charge un fichier JSON OPERAT depuis backend/config/.

    LRU cache pour éviter relectures (lecture une seule fois au boot).
    """
    path = _CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Config OPERAT manquant : {path}. Vérifier commit 6201c44e (sources OPERAT v0.9 livrées Sprint C-1)."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_zone_for_annexe_i(zone: str) -> str:
    """Normalise les noms de zones DOM pour matcher l'index Annexe I.

    Annexe III officielle : "Réunion" (avec accent — cf. enum).
    Annexe I JSON extraction : "Reunion" (sans accent — encodage parser PDF).
    Le service accepte les deux formes en entrée et normalise vers la forme JSON.
    """
    mapping = {
        "Réunion": "Reunion",
        "La Réunion": "Reunion",
        "La Reunion": "Reunion",
    }
    return mapping.get(zone, zone)


# ─── Service principal ────────────────────────────────────────────────────────


class OperatValeursAbsoluesService:
    """SoT chaîne 4 lookups OPERAT.

    Usage typique :
        from regops.services.operat_cabs_service import OperatValeursAbsoluesService

        service = OperatValeursAbsoluesService()
        result = service.compute_cabs_2030(
            code_postal="75001",
            altitude_m=35,
            sous_categories_declared=[
                {"title": "Bureaux standards (toutes categories tertiaires confondues)",
                 "surface_m2": 1500},
            ],
        )
        # → {"cabs_2030_kwh_m2_an": ..., "components": [...], "tracability_complete": {...}}
    """

    def __init__(self) -> None:
        self._annexe_i = _load_json(_ANNEXE_I_FILENAME)
        self._annexe_ii = _load_json(_ANNEXE_II_FILENAME)

    # ─── Lookup 1 : code postal → zone climatique ───

    @staticmethod
    def resolve_zone(code_postal: str) -> Optional[str]:
        """Résolution code postal → zone climatique (délègue à `regops.operat_zones`).

        Returns None si COM (975/977/978) ou code postal invalide.
        """
        from regops.operat_zones import resolve_zone_from_postal_code

        return resolve_zone_from_postal_code(code_postal)

    # ─── Lookup 2 : altitude → palier (palier strict, sans interpolation) ───

    @staticmethod
    def resolve_palier_altitude(altitude_m: float) -> str:
        """Palier altitude strict (5 paliers Annexe I).

        ⚠️ Pas d'interpolation entre paliers — palier strict obligatoire.
        Bornes :
        - alt_lt_400      : < 400 m
        - alt_400_800     : 400 ≤ alt < 800 m
        - alt_800_1200    : 800 ≤ alt < 1200 m
        - alt_1200_1600   : 1200 ≤ alt < 1600 m
        - alt_gte_1600    : ≥ 1600 m
        """
        if altitude_m is None:
            raise ValueError("Altitude requise (None reçu)")
        if altitude_m < 0:
            raise ValueError(f"Altitude négative invalide : {altitude_m}")
        if altitude_m < 400:
            return "alt_lt_400"
        if altitude_m < 800:
            return "alt_400_800"
        if altitude_m < 1200:
            return "alt_800_1200"
        if altitude_m < 1600:
            return "alt_1200_1600"
        return "alt_gte_1600"

    # ─── Lookup 3 : sous-cat × zone × palier → CVCi + USEi + IIU ───

    def get_cvci_usei(
        self,
        sous_categorie_title: str,
        zone: str,
        palier_altitude: str,
    ) -> Optional[dict]:
        """Récupère CVCi + USEi étalon + IIU pour une sous-cat × zone × palier.

        Returns None si zone hors index ou palier invalide.
        Raises OperatSousCategorieIntrouvableError si sous-cat absente.
        """
        zone_normalized = _normalize_zone_for_annexe_i(zone)

        zones_order = self._annexe_i.get("zones_order", [])
        if zone_normalized not in zones_order:
            return None
        zone_idx = zones_order.index(zone_normalized)

        if palier_altitude not in self._annexe_i.get("paliers_order", []):
            return None

        for cat in self._annexe_i.get("categories", []):
            for sc in cat.get("sub_categories", []):
                if sc.get("title") == sous_categorie_title:
                    cvc_palier = sc.get("cvc_kwh_m2_an", {}).get(palier_altitude, [])
                    if zone_idx >= len(cvc_palier):
                        return None
                    cvc_value = cvc_palier[zone_idx]

                    return {
                        "cvc_kwh_m2_an": cvc_value,
                        "use_etalon_kwh_m2_an": sc.get("use_etalon_kwh_m2_an"),
                        "part_use_variable": sc.get("part_use_variable"),
                        "iiu_block_raw": sc.get("iiu_block_raw"),
                        "modulation_formula": sc.get("modulation_formula"),
                        "naf": sc.get("naf"),
                        "category_num": cat.get("num"),
                        "category_name": cat.get("name"),
                        "tracability": {
                            "nor": "ATDL2430864A",
                            "date_arrete": "2025-08-01",
                            "annexe": "I",
                            "url_bulletin_officiel": (
                                "https://www.bulletin-officiel.developpement-durable.gouv.fr"
                                "/documents/Bulletinofficiel-0034142/"
                            ),
                            "sous_categorie": sous_categorie_title,
                            "zone": zone,
                            "zone_normalized": zone_normalized,
                            "palier": palier_altitude,
                        },
                    }

        raise OperatSousCategorieIntrouvableError(
            f"Sous-catégorie '{sous_categorie_title}' non trouvée dans Annexe I "
            f"({sum(len(c.get('sub_categories', [])) for c in self._annexe_i.get('categories', []))} sous-cat)"
        )

    # ─── Lookup 4 : sous-cat → groupe G1-G13 → Coeff_ch / Coeff_fr ───

    def get_coeff_dju(self, sous_categorie_title: str) -> Optional[dict]:
        """Récupère le groupe Coeff DJU (G1-G13) pour une sous-catégorie.

        Returns None si la sous-cat n'a pas de groupe DJU rattaché (rare mais possible).
        """
        for groupe in self._annexe_ii.get("groupes", []):
            if sous_categorie_title in groupe.get("categories_couvertes", []):
                return {
                    "groupe_id": groupe["groupe_id"],
                    "coeff_ch_par_dj": groupe["coeff_ch_par_dj"],
                    "coeff_fr_par_dj": groupe["coeff_fr_par_dj"],
                    "description": groupe.get("description"),
                    "tracability": {
                        "nor": "ATDL2430864A",
                        "date_arrete": "2025-08-01",
                        "annexe": "II",
                        "groupe_id": groupe["groupe_id"],
                    },
                }
        return None

    # ─── Compute Cabs 2030 ajusté DJU + IIU ───

    def compute_cabs_2030(
        self,
        code_postal: str,
        altitude_m: float,
        sous_categories_declared: list[dict],
        dju_chauffage_site: Optional[float] = None,
        dju_refroidissement_site: Optional[float] = None,
        dju_chauffage_etalon: Optional[float] = None,
        dju_refroidissement_etalon: Optional[float] = None,
    ) -> dict:
        """Calcul Cabs 2030 ajusté pour un site multi-sous-catégories.

        Cabs = Σ pondérée (surface × (CVC ajusté DJU + USE étalon)) / surface_totale.

        Args:
            code_postal: code postal du site (résolution zone).
            altitude_m: altitude du site (résolution palier strict).
            sous_categories_declared: liste de {title, surface_m2} pour chaque
                sous-cat déclarée sur le site (1 site = N bâtiments × M sous-cat).
            dju_*_site / dju_*_etalon: DJU réels site et étalons (optionnels — si
                None, pas de modulation DJU appliquée → CVC = CVC étalon).

        Returns:
            dict avec :
              - cabs_2030_kwh_m2_an (float, arrondi 2 décimales)
              - components (liste détaillée par sous-cat)
              - surface_totale_m2 (float)
              - tracability_complete (NOR + URLs + flags modulation)

        Raises:
            OperatNonAssujettiError: si COM hors périmètre.
            OperatSousCategorieIntrouvableError: si sous-cat invalide.
            ValueError: si surface totale nulle ou paramètres invalides.
        """
        # Lookup 1 — Zone
        zone = self.resolve_zone(code_postal)
        if zone is None:
            raise OperatNonAssujettiError(
                f"Code postal {code_postal} hors périmètre OPERAT (COM 975/977/978 ou invalide)"
            )

        # Lookup 2 — Palier (lève ValueError si altitude invalide)
        palier = self.resolve_palier_altitude(altitude_m)

        if not sous_categories_declared:
            raise ValueError("Aucune sous-catégorie déclarée")

        # Lookups 3+4 par sous-cat + ajustement DJU
        components = []
        surface_totale = 0.0

        modulation_dju_active = all(
            v is not None
            for v in [
                dju_chauffage_site,
                dju_chauffage_etalon,
                dju_refroidissement_site,
                dju_refroidissement_etalon,
            ]
        )

        for sc_decl in sous_categories_declared:
            title = sc_decl["title"]
            surface = float(sc_decl["surface_m2"])
            surface_totale += surface

            cvci_usei = self.get_cvci_usei(title, zone, palier)
            if cvci_usei is None:
                raise OperatSousCategorieIntrouvableError(
                    f"Sous-catégorie '{title}' introuvable pour zone={zone}, palier={palier}"
                )

            coeff_dju = self.get_coeff_dju(title)

            cvc_ajuste = cvci_usei["cvc_kwh_m2_an"]
            if modulation_dju_active and coeff_dju:
                # Formule arrêté art. 5 : ajustement linéaire DJU
                delta_ch = (dju_chauffage_site - dju_chauffage_etalon) * coeff_dju["coeff_ch_par_dj"]
                delta_fr = (dju_refroidissement_site - dju_refroidissement_etalon) * coeff_dju["coeff_fr_par_dj"]
                cvc_ajuste = cvc_ajuste + delta_ch + delta_fr

            # USE étalon (modulation IIU non implémentée MVP — TODO sprint futur)
            use_module = cvci_usei.get("use_etalon_kwh_m2_an") or 0.0

            components.append(
                {
                    "title": title,
                    "surface_m2": surface,
                    "cvc_etalon_kwh_m2_an": cvci_usei["cvc_kwh_m2_an"],
                    "cvc_ajuste_kwh_m2_an": cvc_ajuste,
                    "use_etalon_kwh_m2_an": use_module,
                    "coeff_dju": coeff_dju,
                    "tracability": cvci_usei["tracability"],
                }
            )

        if surface_totale <= 0:
            raise ValueError("Surface totale nulle ou négative")

        # Pondération surface
        cabs_2030 = sum(
            (c["surface_m2"] / surface_totale) * (c["cvc_ajuste_kwh_m2_an"] + c["use_etalon_kwh_m2_an"])
            for c in components
        )

        return {
            "cabs_2030_kwh_m2_an": round(cabs_2030, 2),
            "components": components,
            "surface_totale_m2": surface_totale,
            "tracability_complete": {
                "code_postal": code_postal,
                "zone": zone,
                "altitude_m": altitude_m,
                "palier_altitude": palier,
                "nor_annexe_i": "ATDL2430864A (annexe I)",
                "nor_annexe_ii": "ATDL2430864A (annexe II)",
                "nor_zones": "LOGL2005904A v2 (annexe III)",
                "date_arrete": "2025-08-01",
                "modulation_dju_active": modulation_dju_active,
                "modulation_iiu_active": False,  # MVP — TODO sprint futur
            },
        }
