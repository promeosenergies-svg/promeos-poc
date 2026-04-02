"""
PROMEOS — Modèles Power Intelligence.

PowerReading : courbe de charge (CDC) en kW par compteur.
PowerContract : paramètres contractuels de puissance par poste (PS, FTA, type compteur).
HCPlageReference : plages horaires heures creuses codifiées (C15 Enedis).

Sources Enedis : R63 (CDC), C12 (contrats), C68 (données techniques), C15 (HC).
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, Date, Boolean
from sqlalchemy.orm import relationship
from .base import Base


# ── FTA TURPE 7 complètes (XSD C12 v1.12.4) ─────────────────────────────

FTA_SEGMENTS = {
    # BT > 36 kVA (C4)
    "BTSUPCU4": {"desc": "BT>36kVA Courte Utilisation", "postes": ["HPH", "HCH", "HPE", "HCE"]},
    "BTSUPLU4": {"desc": "BT>36kVA Longue Utilisation", "postes": ["Pointe", "HPH", "HCH", "HPE", "HCE"]},
    "BTSUPCUACC": {"desc": "BT>36kVA CU Autoconso Collective", "postes": ["HPH", "HCH", "HPE", "HCE"]},
    "BTSUPLUACC": {"desc": "BT>36kVA LU Autoconso Collective", "postes": ["Pointe", "HPH", "HCH", "HPE", "HCE"]},
    # HTA (C2)
    "HTACU5": {"desc": "HTA Courte Utilisation", "postes": ["Pointe", "HPH", "HCH", "HPE", "HCE"]},
    "HTALU5": {"desc": "HTA Longue Utilisation", "postes": ["Pointe", "HPH", "HCH", "HPE", "HCE"]},
    "HTACUPM5": {"desc": "HTA Courte Util. Période Mobile", "postes": ["PM", "HPH", "HCH", "HPE", "HCE"]},
    "HTALUPM5": {"desc": "HTA Longue Util. Période Mobile", "postes": ["PM", "HPH", "HCH", "HPE", "HCE"]},
    "HTAST5": {"desc": "HTA Stockeur (TURPE 7 nouveau)", "postes": ["Pointe", "HPH", "HCH", "HPE", "HCE"]},
    # HTA historique
    "HTA5": {"desc": "HTA 5 postes (TURPE 4)", "postes": ["Pointe", "HPH", "HPE", "HCH", "HCE"]},
    "HTA8": {
        "desc": "HTA 8 postes (TURPE 4)",
        "postes": ["Pointe", "HPH", "HPDemiSaison", "HPE", "HCDemiSaison", "HCH", "HCE", "JA"],
    },
    "HTASansDiff": {"desc": "HTA sans différenciation", "postes": ["Base"]},
    # BT < 36 kVA (C5/Linky)
    "BTINFCUST": {"desc": "BT<36kVA CU sans différenciation", "postes": ["Base"]},
    "BTINFMUDT": {"desc": "BT<36kVA MU HP/HC", "postes": ["HP", "HC"]},
    "BTINFCU4": {"desc": "BT<36kVA CU HP/HC 2 saisons", "postes": ["HP", "HC"]},
    "BTINFMU4": {"desc": "BT<36kVA MU HP/HC 2 saisons", "postes": ["HP", "HC"]},
    "BTINFLU": {"desc": "BT<36kVA LU sans différenciation", "postes": ["Base"]},
}

# Types de compteurs produisant une CDC
COMPTEURS_CDC = {
    "CJE",
    "CJEMdisjoncteur",
    "CJEMcontroleur",
    "CVE",
    "CVEMavecTC",
    "CVEMsansTC",
    "CVEM1",
    "CVEM2",
    "CVEM3",
    "ICE",
    "PME-PMI",
    "SAPHIR",
    "Linky",
}

# Compteurs produisant le DQ (dépassement quadratique)
COMPTEURS_DEPASSEMENT_DQ = {"CVE", "ICE", "PME-PMI", "SAPHIR"}

# PA (puissance atteinte) en kVA vs kW selon type compteur
COMPTEURS_PA_KVA = {"CJE", "CJEMdisjoncteur", "CJEMcontroleur", "CVEMavecTC", "CVEMsansTC", "CVEM1", "CVEM2"}
COMPTEURS_PA_KW = {"CVEM3", "ICE", "PME-PMI", "SAPHIR"}


# ── Modèles SQLAlchemy ────────────────────────────────────────────────────


class PowerReading(Base):
    """
    Courbe de charge (CDC) par compteur.
    Source : Enedis R63 (JSON, flux R4X ou R63A/B).

    Unité stockée : kW (converti depuis Watts à l'ingestion, jamais à l'analyse).
    Horodate : débutante UTC (normalisée depuis finissante C5).
    """

    __tablename__ = "power_readings"

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)

    # Horodate débutante UTC
    ts_debut = Column(DateTime, nullable=False, index=True)
    pas_minutes = Column(Integer, nullable=False, default=30)

    # Grandeurs physiques (après conversion W→kW, VAr→kVAr)
    P_active_kw = Column(Float, nullable=True)
    P_reactive_ind_kvar = Column(Float, nullable=True)
    P_reactive_cap_kvar = Column(Float, nullable=True)
    tension_v = Column(Float, nullable=True)

    # Sens de mesure
    sens = Column(String(10), nullable=False, default="CONS")  # CONS | PROD

    # Qualité des données
    mode_calcul = Column(String(10), nullable=True)  # BRUT | BEST
    nature_point = Column(String(5), nullable=True)  # M=mesuré, E=estimé, C=corrigé
    indice_vraisemblance = Column(Integer, nullable=True, default=0)

    # Classification tarifaire
    periode_tarif = Column(String(20), nullable=True)

    # Traçabilité source
    source_flux = Column(String(10), nullable=True)  # R63|R63A|R63B|R4Q|synthetic
    imported_at = Column(DateTime, nullable=True)

    meter = relationship("Meter", back_populates="power_readings")


class PowerContract(Base):
    """
    Paramètres contractuels de puissance par compteur (PDL/PRM).
    Source : Enedis C12 (événementiel) et C68 (à la demande).

    RÈGLE CLÉ : La PS N'EST PAS une valeur unique.
    ps_par_poste_kva = {"HPH": 250, "HCH": 200, "Pointe": 180, ...} (integer kVA)
    """

    __tablename__ = "power_contracts"

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)

    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=True)  # NULL = contrat actif

    domaine_tension = Column(String(10), nullable=False)  # BT | BTSUP | HTA | HTB
    fta_code = Column(String(20), nullable=False)  # HTACU5, BTSUPCU4, etc.
    type_compteur = Column(String(20), nullable=True)  # CJE|CVE|ICE|PME-PMI|SAPHIR|Linky

    # PS par poste (JSON, integer kVA)
    ps_par_poste_kva = Column(JSON, nullable=True)

    # Puissances réseau
    p_raccordement_kva = Column(Integer, nullable=True)
    p_limite_soutirage_kva = Column(Integer, nullable=True)
    tension_contractuelle_v = Column(Float, nullable=True)

    has_periode_mobile = Column(Boolean, default=False)

    # Historique modifications PS
    date_derniere_augmentation_ps = Column(Date, nullable=True)
    date_derniere_diminution_ps = Column(Date, nullable=True)
    date_derniere_modif_fta = Column(Date, nullable=True)

    # Traçabilité
    source_flux = Column(String(10), nullable=True)  # C12|C68|manual
    created_at = Column(DateTime, nullable=True)

    meter = relationship("Meter", back_populates="power_contracts")


class HCPlageReference(Base):
    """
    Table de référence des plages horaires heures creuses.
    Source : C15 v5.1.3 guide Enedis (§5.5.3) — 100+ plages codifiées.
    HC saisonnalisées (actif sept 2026) : SAISON_HAUTE (nov-mars) / SAISON_BASSE (avr-oct).
    """

    __tablename__ = "hc_plage_references"

    id = Column(Integer, primary_key=True)
    libelle = Column(String(255), nullable=False)
    # Segments horaires parsés : [{"debut": "01:00", "fin": "07:00"}, ...]
    segments = Column(JSON, nullable=False)
    saison = Column(String(20), nullable=True)  # SAISON_HAUTE | SAISON_BASSE | null
    is_active = Column(Boolean, default=True)
