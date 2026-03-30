"""PROMEOS -- Enedis R50 CDC C5 XML parser.

Parses decrypted XML bytes into typed dataclasses. No DB access. No side effects.
All values are preserved as raw strings from the XML -- no type conversion.

XML structure (Enedis ADR V70 -- R50 Courbe de charge C5):
  <R50>
    <En_Tete_Flux>
      <Identifiant_Flux>R50</Identifiant_Flux>
      <Libelle_Flux>Courbes de charge des PRM du segment C5 sur abonnement</Libelle_Flux>
      <Version_XSD>1.1.0</Version_XSD>
      <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>
      <Identifiant_Destinataire>...</Identifiant_Destinataire>
      <Date_Creation>...</Date_Creation>
      <Identifiant_Contrat>...</Identifiant_Contrat>
      <Numero_Abonnement>...</Numero_Abonnement>
      <Pas_Publication>30</Pas_Publication>
    </En_Tete_Flux>
    <PRM>   (1..N)
      <Id_PRM>14-digit PRM</Id_PRM>
      <Donnees_Releve>  (1..N per PRM)
        <Date_Releve>2023-01-02</Date_Releve>
        <Id_Affaire>M041AWXF</Id_Affaire>
        <PDC>  (0..48 per releve for 30-min steps)
          <H>2023-01-02T16:30:00+01:00</H>
          <V>20710</V>
          <IV>0</IV>
        </PDC>
      </Donnees_Releve>
    </PRM>
  </R50>

Tolerances:
  - xmlns:xsi namespace attribute on root -> stripped transparently
  - PDC with only <H> (no <V> or <IV>) -> valeur=None, indice_vraisemblance=None
  - Empty PRM list (valid XML, 0 PRMs) -> empty list, no error
  - Empty Donnees_Releve (0 PDC) -> empty points list, no error
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from data_ingestion.enedis.parsers._helpers import (
    child_text, find_child, header_to_dict, parse_xml_root, strip_ns,
)


class R50ParseError(Exception):
    """Raised when XML is structurally invalid for R50 format."""


@dataclass
class ParsedR50Point:
    """A single PDC (point de courbe) -- raw strings."""

    horodatage: str  # H - ISO8601 with timezone
    valeur: str | None  # V - raw string, None if absent
    indice_vraisemblance: str | None  # IV - "0"/"1", None if absent


@dataclass
class ParsedR50Releve:
    """A Donnees_Releve block with its context and points."""

    date_releve: str  # Date_Releve
    id_affaire: str | None  # Id_Affaire (optional)
    points: list[ParsedR50Point] = field(default_factory=list)


@dataclass
class ParsedR50PRM:
    """A PRM block with all its releves."""

    point_id: str  # Id_PRM
    releves: list[ParsedR50Releve] = field(default_factory=list)


@dataclass
class ParsedR50Header:
    """All En_Tete_Flux fields as a raw dict."""

    raw: dict  # All En_Tete_Flux child elements as {tag: text}


@dataclass
class ParsedR50File:
    """Complete parse result for one R50 file."""

    header: ParsedR50Header
    prms: list[ParsedR50PRM] = field(default_factory=list)

    @property
    def total_measures(self) -> int:
        return sum(len(r.points) for prm in self.prms for r in prm.releves)


def parse_r50(xml_bytes: bytes) -> ParsedR50File:
    """Parse decrypted R50 XML bytes into a ParsedR50File.

    Args:
        xml_bytes: Decrypted XML content (bytes) from decrypt_file().

    Returns:
        ParsedR50File with header and all PRM blocks.

    Raises:
        R50ParseError: XML structure is not valid R50 (missing root,
            En_Tete_Flux, Id_PRM, Date_Releve, or H in PDC).
    """
    root = parse_xml_root(xml_bytes, "R50", R50ParseError)

    en_tete = find_child(root, "En_Tete_Flux")
    if en_tete is None:
        raise R50ParseError("Missing <En_Tete_Flux> element")

    header_raw = header_to_dict(en_tete)

    header = ParsedR50Header(raw=header_raw)

    # Parse all PRM blocks
    prms: list[ParsedR50PRM] = []
    for elem in root:
        if strip_ns(elem.tag) != "PRM":
            continue
        prm = _parse_prm(elem)
        prms.append(prm)

    return ParsedR50File(header=header, prms=prms)


def _parse_prm(prm_elem: ET.Element) -> ParsedR50PRM:
    """Parse a single <PRM> element."""
    id_prm = child_text(prm_elem, "Id_PRM")
    if not id_prm:
        raise R50ParseError("Missing or empty <Id_PRM> in PRM block")

    releves: list[ParsedR50Releve] = []
    for child in prm_elem:
        if strip_ns(child.tag) != "Donnees_Releve":
            continue
        releve = _parse_donnees_releve(child)
        releves.append(releve)

    return ParsedR50PRM(point_id=id_prm, releves=releves)


def _parse_donnees_releve(releve_elem: ET.Element) -> ParsedR50Releve:
    """Parse a single <Donnees_Releve> element."""
    date_releve = child_text(releve_elem, "Date_Releve")
    if not date_releve:
        raise R50ParseError("Missing or empty <Date_Releve> in Donnees_Releve")

    id_affaire = child_text(releve_elem, "Id_Affaire")

    points: list[ParsedR50Point] = []
    for child in releve_elem:
        if strip_ns(child.tag) != "PDC":
            continue
        point = _parse_pdc(child)
        points.append(point)

    return ParsedR50Releve(date_releve=date_releve, id_affaire=id_affaire, points=points)


def _parse_pdc(pdc_elem: ET.Element) -> ParsedR50Point:
    """Parse a single <PDC> element."""
    horodatage = child_text(pdc_elem, "H")
    if not horodatage:
        raise R50ParseError("Missing or empty <H> in PDC element")

    valeur = child_text(pdc_elem, "V")
    indice_vraisemblance = child_text(pdc_elem, "IV")

    return ParsedR50Point(
        horodatage=horodatage,
        valeur=valeur,
        indice_vraisemblance=indice_vraisemblance,
    )
