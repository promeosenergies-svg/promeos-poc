"""PROMEOS — Enedis R171 index flux XML parser.

Parses decrypted XML bytes into typed dataclasses. No DB access. No side effects.
All values are preserved as raw strings from the XML — no type conversion.

XML structure (ADR V70 R171):
  <ns2:R171 xmlns:ns2="http://www.enedis.fr/stm/R171">
    <entete>
      <emetteur>Enedis</emetteur>
      <destinataire>GRD-F121</destinataire>
      <dateHeureCreation>2026-03-01T01:13:01</dateHeureCreation>
      <flux>R171</flux>
      <version>1.0</version>
    </entete>
    <serieMesuresDateesListe>
      <serieMesuresDatees>
        <prmId>30000550506121</prmId>
        <type>INDEX</type>
        <grandeurMetier>CONS</grandeurMetier>
        <grandeurPhysique>EA</grandeurPhysique>
        <typeCalendrier>D</typeCalendrier>
        <codeClasseTemporelle>HPH</codeClasseTemporelle>
        <libelleClasseTemporelle>Heures Pleines Hiver</libelleClasseTemporelle>
        <unite>Wh</unite>
        <mesuresDateesListe>
          <mesureDatee>
            <dateFin>2026-03-01T00:51:11</dateFin>
            <valeur>1320</valeur>
          </mesureDatee>
        </mesuresDateesListe>
      </serieMesuresDatees>
    </serieMesuresDateesListe>
  </ns2:R171>

Tolerances:
  - Namespace (ns2) is optional — works with or without
  - Missing optional fields (grandeurMetier, etc.) → stored as None
  - Empty mesuresDateesListe (valid XML, 0 mesures) → empty list, no error
  - Empty serieMesuresDateesListe → empty list, no error
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from data_ingestion.enedis.parsers._helpers import child_text, find_child, strip_ns


class R171ParseError(Exception):
    """Raised when XML is structurally invalid for R171 format."""


@dataclass
class ParsedR171Mesure:
    """A single mesureDatee — raw strings."""

    date_fin: str  # dateFin - ISO8601 without timezone, as-is from XML
    valeur: str | None  # Raw string value, or None if element absent


@dataclass
class ParsedR171Serie:
    """A serieMesuresDatees block with its context and mesures."""

    point_id: str  # prmId
    type_mesure: str  # type (INDEX)
    grandeur_metier: str | None
    grandeur_physique: str | None
    type_calendrier: str | None
    code_classe_temporelle: str | None
    libelle_classe_temporelle: str | None
    unite: str | None
    mesures: list[ParsedR171Mesure] = field(default_factory=list)


@dataclass
class ParsedR171Header:
    """All entete fields as a raw dict."""

    raw: dict  # All entete child elements as {tag: text}


@dataclass
class ParsedR171File:
    """Complete parse result for one R171 file."""

    header: ParsedR171Header
    series: list[ParsedR171Serie] = field(default_factory=list)

    @property
    def total_measures(self) -> int:
        return sum(len(s.mesures) for s in self.series)


def parse_r171(xml_bytes: bytes) -> ParsedR171File:
    """Parse decrypted R171 XML bytes into a ParsedR171File.

    Args:
        xml_bytes: Decrypted XML content (bytes) from decrypt_file().

    Returns:
        ParsedR171File with header and all serieMesuresDatees blocks.

    Raises:
        R171ParseError: XML structure is not valid R171 (missing root, entete,
            serieMesuresDateesListe, or prmId).
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise R171ParseError(f"Invalid XML: {exc}") from exc

    # Root must be <R171> (namespace-stripped)
    root_tag = strip_ns(root.tag)
    if root_tag != "R171":
        raise R171ParseError(f"Expected root <R171>, got <{root_tag}>")

    # Parse entete
    entete = find_child(root, "entete")
    if entete is None:
        raise R171ParseError("Missing <entete> element")

    header_raw: dict = {}
    for child in entete:
        tag = strip_ns(child.tag)
        header_raw[tag] = (child.text or "").strip()

    header = ParsedR171Header(raw=header_raw)

    # Parse serieMesuresDateesListe
    series_liste = find_child(root, "serieMesuresDateesListe")
    if series_liste is None:
        raise R171ParseError("Missing <serieMesuresDateesListe> element")

    # Parse each serieMesuresDatees
    series: list[ParsedR171Serie] = []
    for serie_elem in series_liste:
        if strip_ns(serie_elem.tag) != "serieMesuresDatees":
            continue
        serie = _parse_serie(serie_elem)
        series.append(serie)

    return ParsedR171File(header=header, series=series)


def _parse_serie(serie_elem: ET.Element) -> ParsedR171Serie:
    """Parse a single <serieMesuresDatees> element."""
    prm_id = child_text(serie_elem, "prmId")
    if not prm_id:
        raise R171ParseError("Missing or empty <prmId> in serieMesuresDatees")

    type_mesure = child_text(serie_elem, "type")
    if not type_mesure:
        raise R171ParseError("Missing or empty <type> in serieMesuresDatees")

    serie = ParsedR171Serie(
        point_id=prm_id,
        type_mesure=type_mesure,
        grandeur_metier=child_text(serie_elem, "grandeurMetier"),
        grandeur_physique=child_text(serie_elem, "grandeurPhysique"),
        type_calendrier=child_text(serie_elem, "typeCalendrier"),
        code_classe_temporelle=child_text(serie_elem, "codeClasseTemporelle"),
        libelle_classe_temporelle=child_text(serie_elem, "libelleClasseTemporelle"),
        unite=child_text(serie_elem, "unite"),
    )

    mesures_liste = find_child(serie_elem, "mesuresDateesListe")
    if mesures_liste is None:
        # No mesures container → empty list (not an error)
        return serie

    for mesure_elem in mesures_liste:
        if strip_ns(mesure_elem.tag) != "mesureDatee":
            continue

        date_fin = child_text(mesure_elem, "dateFin")
        if not date_fin:
            raise R171ParseError("Missing or empty <dateFin> in mesureDatee")

        valeur = child_text(mesure_elem, "valeur")

        serie.mesures.append(
            ParsedR171Mesure(date_fin=date_fin, valeur=valeur)
        )

    return serie
