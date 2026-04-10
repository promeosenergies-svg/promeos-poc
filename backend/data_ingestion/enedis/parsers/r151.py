"""PROMEOS — Enedis R151 index + puissance maximale C5 XML parser.

Parses decrypted XML bytes into typed dataclasses. No DB access. No side effects.
All values are preserved as raw strings from the XML — no type conversion.

XML structure (Enedis ADR V70 — R151):
  <R151>
    <En_Tete_Flux>
      <Identifiant_Flux>R151</Identifiant_Flux>
      <Libelle_Flux>Puissances maximales et index des PRM du segment C5 sur abonnement</Libelle_Flux>
      <Version_XSD>V1</Version_XSD>
      <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>
      <Identifiant_Destinataire>...</Identifiant_Destinataire>
      <Date_Creation>...</Date_Creation>
      <Identifiant_Contrat>...</Identifiant_Contrat>
      <Numero_Abonnement>...</Numero_Abonnement>
      <Unite_Mesure_Index>Wh</Unite_Mesure_Index>
      <Unite_Mesure_Puissance>VA</Unite_Mesure_Puissance>
    </En_Tete_Flux>
    <PRM>
      <Id_PRM>14-digit PRM</Id_PRM>
      <Donnees_Releve>
        <Date_Releve>2024-12-17</Date_Releve>
        <Id_Calendrier_Fournisseur>...</Id_Calendrier_Fournisseur>
        <Libelle_Calendrier_Fournisseur>...</Libelle_Calendrier_Fournisseur>
        <Id_Calendrier_Distributeur>...</Id_Calendrier_Distributeur>
        <Libelle_Calendrier_Distributeur>...</Libelle_Calendrier_Distributeur>
        <Id_Affaire>...</Id_Affaire>
        <Classe_Temporelle_Distributeur>
          <Id_Classe_Temporelle>HCB</Id_Classe_Temporelle>
          <Libelle_Classe_Temporelle>...</Libelle_Classe_Temporelle>
          <Rang_Cadran>1</Rang_Cadran>
          <Valeur>83044953</Valeur>
          <Indice_Vraisemblance>0</Indice_Vraisemblance>
        </Classe_Temporelle_Distributeur>
        <Classe_Temporelle>
          <Id_Classe_Temporelle>HC</Id_Classe_Temporelle>
          <Libelle_Classe_Temporelle>...</Libelle_Classe_Temporelle>
          <Rang_Cadran>1</Rang_Cadran>
          <Valeur>18047813</Valeur>
          <Indice_Vraisemblance>0</Indice_Vraisemblance>
        </Classe_Temporelle>
        <Puissance_Maximale>
          <Valeur>7452</Valeur>
        </Puissance_Maximale>
      </Donnees_Releve>
    </PRM>
  </R151>

Tolerances:
  - xmlns:xsi namespace attributes are stripped
  - Missing optional fields -> stored as None
  - Releve with 0 donnees -> empty list, no error
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from data_ingestion.enedis.parsers._helpers import (
    child_text,
    find_child,
    header_to_dict,
    parse_xml_root,
    strip_ns,
)


class R151ParseError(Exception):
    """Raised when XML is structurally invalid for R151 format."""


@dataclass
class ParsedR151Donnee:
    """One data value from R151: index by classe temporelle OR puissance max."""

    type_donnee: str  # CT_DIST / CT / PMAX
    id_classe_temporelle: str | None  # HCB/HCH/HPB/HPH/HC/HP, None for PMAX
    libelle_classe_temporelle: str | None  # None for PMAX
    rang_cadran: str | None  # None for PMAX
    valeur: str | None  # Index Wh or puissance VA
    indice_vraisemblance: str | None  # 0-15, None for PMAX


@dataclass
class ParsedR151Releve:
    """A Donnees_Releve block with its context and donnees."""

    date_releve: str  # Date_Releve
    id_calendrier_fournisseur: str | None
    libelle_calendrier_fournisseur: str | None
    id_calendrier_distributeur: str | None
    libelle_calendrier_distributeur: str | None
    id_affaire: str | None
    donnees: list[ParsedR151Donnee] = field(default_factory=list)


@dataclass
class ParsedR151PRM:
    """One PRM block from R151."""

    point_id: str  # Id_PRM
    releves: list[ParsedR151Releve] = field(default_factory=list)


@dataclass
class ParsedR151Header:
    """All En_Tete_Flux fields as a raw dict."""

    raw: dict  # All En_Tete_Flux children as {tag: text}


@dataclass
class ParsedR151File:
    """Complete parse result for one R151 file."""

    header: ParsedR151Header
    prms: list[ParsedR151PRM] = field(default_factory=list)

    @property
    def total_measures(self) -> int:
        return sum(len(r.donnees) for prm in self.prms for r in prm.releves)


def parse_r151(xml_bytes: bytes) -> ParsedR151File:
    """Parse decrypted R151 XML bytes into a ParsedR151File.

    Args:
        xml_bytes: Decrypted XML content (bytes).

    Returns:
        ParsedR151File with header, PRMs, releves, and all donnees.

    Raises:
        R151ParseError: XML structure is not valid R151 (missing root,
            En_Tete_Flux, Id_PRM, or Date_Releve).
    """
    root = parse_xml_root(xml_bytes, "R151", R151ParseError)

    en_tete = find_child(root, "En_Tete_Flux")
    if en_tete is None:
        raise R151ParseError("Missing <En_Tete_Flux> element")

    header_raw = header_to_dict(en_tete)

    header = ParsedR151Header(raw=header_raw)

    # Parse all PRM blocks
    prms = []
    for prm_elem in root:
        if strip_ns(prm_elem.tag) != "PRM":
            continue

        prm_id_elem = find_child(prm_elem, "Id_PRM")
        if prm_id_elem is None or not (prm_id_elem.text or "").strip():
            raise R151ParseError("Missing or empty <Id_PRM>")

        point_id = prm_id_elem.text.strip()

        # Parse all Donnees_Releve blocks
        releves = []
        for releve_elem in prm_elem:
            if strip_ns(releve_elem.tag) != "Donnees_Releve":
                continue
            releve = _parse_donnees_releve(releve_elem)
            releves.append(releve)

        prms.append(ParsedR151PRM(point_id=point_id, releves=releves))

    return ParsedR151File(header=header, prms=prms)


def _parse_donnees_releve(releve_elem: ET.Element) -> ParsedR151Releve:
    """Parse a single <Donnees_Releve> element."""
    date_releve = child_text(releve_elem, "Date_Releve")
    if not date_releve:
        raise R151ParseError("Missing or empty <Date_Releve> in Donnees_Releve")

    releve = ParsedR151Releve(
        date_releve=date_releve,
        id_calendrier_fournisseur=child_text(releve_elem, "Id_Calendrier_Fournisseur"),
        libelle_calendrier_fournisseur=child_text(releve_elem, "Libelle_Calendrier_Fournisseur"),
        id_calendrier_distributeur=child_text(releve_elem, "Id_Calendrier_Distributeur"),
        libelle_calendrier_distributeur=child_text(releve_elem, "Libelle_Calendrier_Distributeur"),
        id_affaire=child_text(releve_elem, "Id_Affaire"),
    )

    # Parse Classe_Temporelle_Distributeur, Classe_Temporelle, and Puissance_Maximale blocks
    for child in releve_elem:
        tag = strip_ns(child.tag)
        if tag == "Classe_Temporelle_Distributeur":
            donnee = ParsedR151Donnee(
                type_donnee="CT_DIST",
                id_classe_temporelle=child_text(child, "Id_Classe_Temporelle"),
                libelle_classe_temporelle=child_text(child, "Libelle_Classe_Temporelle"),
                rang_cadran=child_text(child, "Rang_Cadran"),
                valeur=child_text(child, "Valeur"),
                indice_vraisemblance=child_text(child, "Indice_Vraisemblance"),
            )
            releve.donnees.append(donnee)
        elif tag == "Classe_Temporelle":
            donnee = ParsedR151Donnee(
                type_donnee="CT",
                id_classe_temporelle=child_text(child, "Id_Classe_Temporelle"),
                libelle_classe_temporelle=child_text(child, "Libelle_Classe_Temporelle"),
                rang_cadran=child_text(child, "Rang_Cadran"),
                valeur=child_text(child, "Valeur"),
                indice_vraisemblance=child_text(child, "Indice_Vraisemblance"),
            )
            releve.donnees.append(donnee)
        elif tag == "Puissance_Maximale":
            donnee = ParsedR151Donnee(
                type_donnee="PMAX",
                id_classe_temporelle=None,
                libelle_classe_temporelle=None,
                rang_cadran=None,
                valeur=child_text(child, "Valeur"),
                indice_vraisemblance=None,
            )
            releve.donnees.append(donnee)

    return releve
