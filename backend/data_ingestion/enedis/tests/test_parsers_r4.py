"""Tests for the R4x XML parser — pure parsing, no DB, no encryption."""

import pytest

from data_ingestion.enedis.parsers.r4 import (
    ParsedCourbe,
    ParsedPoint,
    ParsedR4xFile,
    R4xParseError,
    parse_r4x,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic R4x XML
# ---------------------------------------------------------------------------


def _make_r4x_xml(
    prm="30000210411333",
    frequence="H",
    nature="Corrigee",
    destinataire="23X--130624--EE1",
    courbes_xml="",
) -> bytes:
    """Build a minimal valid R4x XML document."""
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Libelle_Flux>Flux de courbes de charge R4x</Libelle_Flux>
    <Identifiant_Emetteur>ENEDIS</Identifiant_Emetteur>
    <Identifiant_Destinataire>{destinataire}</Identifiant_Destinataire>
    <Date_Creation>2026-03-16T15:36:43+01:00</Date_Creation>
    <Frequence_Publication>{frequence}</Frequence_Publication>
    <Reference_Demande>189465931</Reference_Demande>
    <Nature_De_Courbe_Demandee>{nature}</Nature_De_Courbe_Demandee>
  </Entete>
  <Corps>
    <Identifiant_PRM>{prm}</Identifiant_PRM>
    {courbes_xml}
  </Corps>
</Courbe>""".encode("utf-8")


def _make_courbe_xml(
    debut="2026-03-07T00:00:00+01:00",
    fin="2026-03-07T23:59:59+01:00",
    granularite="5",
    unite="kW",
    grandeur_metier="CONS",
    grandeur_physique="EA",
    points_xml="",
) -> str:
    """Build a <Donnees_Courbe> XML fragment."""
    return f"""\
<Donnees_Courbe>
  <Horodatage_Debut>{debut}</Horodatage_Debut>
  <Horodatage_Fin>{fin}</Horodatage_Fin>
  <Granularite>{granularite}</Granularite>
  <Unite_Mesure>{unite}</Unite_Mesure>
  <Grandeur_Metier>{grandeur_metier}</Grandeur_Metier>
  <Grandeur_Physique>{grandeur_physique}</Grandeur_Physique>
  {points_xml}
</Donnees_Courbe>"""


def _make_point_xml(horodatage, valeur=None, statut=None) -> str:
    """Build a <Donnees_Point_Mesure .../> XML fragment."""
    attrs = f'Horodatage="{horodatage}"'
    if valeur is not None:
        attrs += f' Valeur_Point="{valeur}"'
    if statut is not None:
        attrs += f' Statut_Point="{statut}"'
    return f"<Donnees_Point_Mesure {attrs}/>"


# ---------------------------------------------------------------------------
# Tests — Header parsing
# ---------------------------------------------------------------------------


class TestParseR4xHeader:
    def test_header_fields_extracted(self):
        xml = _make_r4x_xml(frequence="M", nature="Brute", destinataire="MY_DEST")
        result = parse_r4x(xml)

        assert result.header.frequence_publication == "M"
        assert result.header.nature_courbe_demandee == "Brute"
        assert result.header.identifiant_destinataire == "MY_DEST"

    def test_header_raw_contains_all_entete_fields(self):
        xml = _make_r4x_xml()
        result = parse_r4x(xml)

        raw = result.header.raw
        assert raw["Identifiant_Flux"] == "R4x"
        assert raw["Libelle_Flux"] == "Flux de courbes de charge R4x"
        assert raw["Identifiant_Emetteur"] == "ENEDIS"
        assert raw["Date_Creation"] == "2026-03-16T15:36:43+01:00"
        assert raw["Reference_Demande"] == "189465931"

    def test_prm_extracted(self):
        xml = _make_r4x_xml(prm="30000140557249")
        result = parse_r4x(xml)
        assert result.point_id == "30000140557249"


# ---------------------------------------------------------------------------
# Tests — Donnees_Courbe parsing
# ---------------------------------------------------------------------------


class TestParseR4xCourbe:
    def test_single_courbe_with_points(self):
        points = "\n".join(
            [
                _make_point_xml("2026-03-07T00:00:00+01:00", "398", "R"),
                _make_point_xml("2026-03-07T00:05:00+01:00", "383", "R"),
                _make_point_xml("2026-03-07T00:10:00+01:00", "386", "E"),
            ]
        )
        courbe = _make_courbe_xml(points_xml=points)
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        assert len(result.courbes) == 1
        c = result.courbes[0]
        assert c.horodatage_debut == "2026-03-07T00:00:00+01:00"
        assert c.horodatage_fin == "2026-03-07T23:59:59+01:00"
        assert c.granularite == "5"
        assert c.unite_mesure == "kW"
        assert c.grandeur_metier == "CONS"
        assert c.grandeur_physique == "EA"
        assert len(c.points) == 3

    def test_point_values_are_raw_strings(self):
        points = _make_point_xml("2026-03-07T00:00:00+01:00", "398", "R")
        courbe = _make_courbe_xml(points_xml=points)
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        p = result.courbes[0].points[0]
        assert p.horodatage == "2026-03-07T00:00:00+01:00"
        assert p.valeur_point == "398"
        assert isinstance(p.valeur_point, str)
        assert p.statut_point == "R"

    def test_missing_valeur_point_is_none(self):
        points = _make_point_xml("2026-03-07T00:00:00+01:00", statut="R")
        courbe = _make_courbe_xml(points_xml=points)
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        assert result.courbes[0].points[0].valeur_point is None

    def test_missing_statut_point_is_none(self):
        points = _make_point_xml("2026-03-07T00:00:00+01:00", valeur="100")
        courbe = _make_courbe_xml(points_xml=points)
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        assert result.courbes[0].points[0].statut_point is None

    def test_multiple_courbes_ea_and_eri(self):
        courbe_ea = _make_courbe_xml(
            grandeur_physique="EA",
            points_xml=_make_point_xml("2026-03-07T00:00:00+01:00", "100", "R"),
        )
        courbe_eri = _make_courbe_xml(
            grandeur_physique="ERI",
            unite="kWr",
            points_xml=_make_point_xml("2026-03-07T00:00:00+01:00", "50", "R"),
        )
        xml = _make_r4x_xml(courbes_xml=courbe_ea + courbe_eri)
        result = parse_r4x(xml)

        assert len(result.courbes) == 2
        assert result.courbes[0].grandeur_physique == "EA"
        assert result.courbes[1].grandeur_physique == "ERI"
        assert result.courbes[1].unite_mesure == "kWr"

    def test_empty_courbe_zero_points(self):
        courbe = _make_courbe_xml(points_xml="")
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        assert len(result.courbes) == 1
        assert len(result.courbes[0].points) == 0

    def test_no_courbes_zero_total(self):
        xml = _make_r4x_xml(courbes_xml="")
        result = parse_r4x(xml)

        assert len(result.courbes) == 0
        assert result.total_measures == 0

    def test_total_measures_across_courbes(self):
        courbe1 = _make_courbe_xml(
            grandeur_physique="EA",
            points_xml="\n".join(
                [
                    _make_point_xml("2026-03-07T00:00:00+01:00", "100", "R"),
                    _make_point_xml("2026-03-07T00:05:00+01:00", "200", "R"),
                ]
            ),
        )
        courbe2 = _make_courbe_xml(
            grandeur_physique="ERI",
            points_xml=_make_point_xml("2026-03-07T00:00:00+01:00", "50", "R"),
        )
        xml = _make_r4x_xml(courbes_xml=courbe1 + courbe2)
        result = parse_r4x(xml)

        assert result.total_measures == 3


# ---------------------------------------------------------------------------
# Tests — Error handling
# ---------------------------------------------------------------------------


class TestParseR4xErrors:
    def test_invalid_xml_raises(self):
        with pytest.raises(R4xParseError, match="Invalid XML"):
            parse_r4x(b"not xml at all")

    def test_wrong_root_tag_raises(self):
        xml = b'<?xml version="1.0"?><NotCourbe/>'
        with pytest.raises(R4xParseError, match="Expected root <Courbe>"):
            parse_r4x(xml)

    def test_missing_entete_raises(self):
        xml = b'<?xml version="1.0"?><Courbe><Corps><Identifiant_PRM>123</Identifiant_PRM></Corps></Courbe>'
        with pytest.raises(R4xParseError, match="Missing <Entete>"):
            parse_r4x(xml)

    def test_missing_corps_raises(self):
        xml = b"""\
<?xml version="1.0"?><Courbe><Entete>
<Identifiant_Flux>R4x</Identifiant_Flux>
</Entete></Courbe>"""
        with pytest.raises(R4xParseError, match="Missing <Corps>"):
            parse_r4x(xml)

    def test_missing_horodatage_attribute_raises(self):
        """Donnees_Point_Mesure without Horodatage must raise, not store empty string."""
        point = '<Donnees_Point_Mesure Valeur_Point="100" Statut_Point="R"/>'
        courbe = _make_courbe_xml(points_xml=point)
        xml = _make_r4x_xml(courbes_xml=courbe)
        with pytest.raises(R4xParseError, match="missing required Horodatage"):
            parse_r4x(xml)

    def test_missing_prm_raises(self):
        xml = b"""\
<?xml version="1.0"?><Courbe><Entete>
<Identifiant_Flux>R4x</Identifiant_Flux>
</Entete><Corps></Corps></Courbe>"""
        with pytest.raises(R4xParseError, match="Missing or empty <Identifiant_PRM>"):
            parse_r4x(xml)


# ---------------------------------------------------------------------------
# Tests — Tolerance
# ---------------------------------------------------------------------------


class TestParseR4xTolerance:
    def test_all_statut_point_codes_accepted(self):
        """All documented Statut_Point values should pass through."""
        codes = ["R", "H", "P", "S", "T", "F", "G", "E", "C", "K", "D"]
        points = "\n".join(
            _make_point_xml(f"2026-03-07T{i:02d}:00:00+01:00", str(i * 100), code) for i, code in enumerate(codes)
        )
        courbe = _make_courbe_xml(points_xml=points)
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        statuts = [p.statut_point for p in result.courbes[0].points]
        assert statuts == codes

    def test_whitespace_in_attributes_stripped(self):
        point = (
            '<Donnees_Point_Mesure Horodatage=" 2026-03-07T00:00:00+01:00 " Valeur_Point=" 398 " Statut_Point=" R "/>'
        )
        courbe = _make_courbe_xml(points_xml=point)
        xml = _make_r4x_xml(courbes_xml=courbe)
        result = parse_r4x(xml)

        p = result.courbes[0].points[0]
        assert p.horodatage == "2026-03-07T00:00:00+01:00"
        assert p.valeur_point == "398"
        assert p.statut_point == "R"
