"""PROMEOS — Enedis R4x (R4H/R4M/R4Q) CDC XML parser.

Parses decrypted XML bytes into typed dataclasses. No DB access. No side effects.
All values are preserved as raw strings from the XML — no type conversion.

XML structure (Enedis.SGE.XSD.0409.R4x_v1.1.1.xsd):
  <Courbe>
    <Entete>
      <Identifiant_Flux>R4x</Identifiant_Flux>
      <Libelle_Flux>...</Libelle_Flux>
      <Identifiant_Emetteur>ENEDIS</Identifiant_Emetteur>
      <Identifiant_Destinataire>...</Identifiant_Destinataire>
      <Date_Creation>...</Date_Creation>
      <Frequence_Publication>H|M|Q</Frequence_Publication>
      <Reference_Demande>...</Reference_Demande>
      <Nature_De_Courbe_Demandee>Brute|Corrigee</Nature_De_Courbe_Demandee>
    </Entete>
    <Corps>
      <Identifiant_PRM>14-digit PRM</Identifiant_PRM>
      <Donnees_Courbe>  (1..N per Corps)
        <Horodatage_Debut>...</Horodatage_Debut>
        <Horodatage_Fin>...</Horodatage_Fin>
        <Granularite>5|10</Granularite>
        <Unite_Mesure>kW|kWr|V</Unite_Mesure>
        <Grandeur_Metier>CONS|PROD</Grandeur_Metier>
        <Grandeur_Physique>EA|ERC|ERI|E</Grandeur_Physique>
        <Donnees_Point_Mesure Horodatage="..." Valeur_Point="..." Statut_Point="R"/>
      </Donnees_Courbe>
    </Corps>
  </Courbe>

Tolerances:
  - ERDF_ prefix (historical) is equivalent to ENEDIS_
  - Missing Statut_Point or Valeur_Point attributes → stored as None
  - Empty Donnees_Courbe (valid XML, 0 points) → empty list, no error
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from data_ingestion.enedis.parsers._helpers import (
    child_text, find_child, header_to_dict, parse_xml_root, strip_ns,
)


class R4xParseError(Exception):
    """Raised when XML is structurally invalid for R4x format."""


@dataclass
class ParsedPoint:
    """A single Donnees_Point_Mesure — raw strings."""

    horodatage: str  # ISO8601 with timezone, as-is from XML
    valeur_point: str | None  # Raw string value, or None if attribute absent
    statut_point: str | None  # R/H/P/S/T/F/G/E/C/K/D, or None


@dataclass
class ParsedCourbe:
    """A Donnees_Courbe block with its context and points."""

    horodatage_debut: str | None
    horodatage_fin: str | None
    granularite: str | None
    unite_mesure: str | None
    grandeur_metier: str | None
    grandeur_physique: str | None
    points: list[ParsedPoint] = field(default_factory=list)


@dataclass
class ParsedR4xHeader:
    """All Entete fields as a raw dict + extracted queryable fields."""

    raw: dict  # All Entete child elements as {tag: text}
    frequence_publication: str | None
    nature_courbe_demandee: str | None
    identifiant_destinataire: str | None


@dataclass
class ParsedR4xFile:
    """Complete parse result for one R4x file."""

    header: ParsedR4xHeader
    point_id: str  # Identifiant_PRM
    courbes: list[ParsedCourbe] = field(default_factory=list)

    @property
    def total_measures(self) -> int:
        return sum(len(c.points) for c in self.courbes)


def parse_r4x(xml_bytes: bytes) -> ParsedR4xFile:
    """Parse decrypted R4x XML bytes into a ParsedR4xFile.

    Args:
        xml_bytes: Decrypted XML content (bytes) from decrypt_file().

    Returns:
        ParsedR4xFile with header, PRM, and all Donnees_Courbe blocks.

    Raises:
        R4xParseError: XML structure is not valid R4x (missing root, Entete,
            Corps, or Identifiant_PRM).
    """
    root = parse_xml_root(xml_bytes, "Courbe", R4xParseError)

    entete = find_child(root, "Entete")
    if entete is None:
        raise R4xParseError("Missing <Entete> element")

    header_raw = header_to_dict(entete)

    header = ParsedR4xHeader(
        raw=header_raw,
        frequence_publication=header_raw.get("Frequence_Publication"),
        nature_courbe_demandee=header_raw.get("Nature_De_Courbe_Demandee"),
        identifiant_destinataire=header_raw.get("Identifiant_Destinataire"),
    )

    # Parse Corps
    corps = find_child(root, "Corps")
    if corps is None:
        raise R4xParseError("Missing <Corps> element")

    prm_elem = find_child(corps, "Identifiant_PRM")
    if prm_elem is None or not (prm_elem.text or "").strip():
        raise R4xParseError("Missing or empty <Identifiant_PRM>")

    point_id = prm_elem.text.strip()

    # Parse all Donnees_Courbe blocks
    courbes = []
    for dc in corps:
        if strip_ns(dc.tag) != "Donnees_Courbe":
            continue
        courbe = _parse_donnees_courbe(dc)
        courbes.append(courbe)

    return ParsedR4xFile(header=header, point_id=point_id, courbes=courbes)


def _parse_donnees_courbe(dc_elem) -> ParsedCourbe:
    """Parse a single <Donnees_Courbe> element."""
    courbe = ParsedCourbe(
        horodatage_debut=child_text(dc_elem, "Horodatage_Debut"),
        horodatage_fin=child_text(dc_elem, "Horodatage_Fin"),
        granularite=child_text(dc_elem, "Granularite"),
        unite_mesure=child_text(dc_elem, "Unite_Mesure"),
        grandeur_metier=child_text(dc_elem, "Grandeur_Metier"),
        grandeur_physique=child_text(dc_elem, "Grandeur_Physique"),
    )

    for child in dc_elem:
        if strip_ns(child.tag) != "Donnees_Point_Mesure":
            continue

        horodatage_raw = (child.get("Horodatage") or "").strip()
        if not horodatage_raw:
            raise R4xParseError("Donnees_Point_Mesure missing required Horodatage attribute")

        valeur_raw = child.get("Valeur_Point")
        statut_raw = child.get("Statut_Point")

        point = ParsedPoint(
            horodatage=horodatage_raw,
            valeur_point=valeur_raw.strip() if valeur_raw is not None else None,
            statut_point=statut_raw.strip() if statut_raw is not None else None,
        )
        courbe.points.append(point)

    return courbe
