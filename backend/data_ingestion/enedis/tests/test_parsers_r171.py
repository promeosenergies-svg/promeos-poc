"""Tests for the R171 XML parser — pure parsing, no DB, no encryption."""

import pytest

from data_ingestion.enedis.parsers.r171 import (
    ParsedR171File,
    ParsedR171Mesure,
    ParsedR171Serie,
    R171ParseError,
    parse_r171,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic R171 XML
# ---------------------------------------------------------------------------


def _make_mesure_xml(date_fin="2026-03-01T00:51:11", valeur=None) -> str:
    """Build a <mesureDatee> XML fragment."""
    parts = [f"<dateFin>{date_fin}</dateFin>"]
    if valeur is not None:
        parts.append(f"<valeur>{valeur}</valeur>")
    return f"<mesureDatee>{''.join(parts)}</mesureDatee>"


def _make_serie_xml(
    prm_id="30000550506121",
    type_mesure="INDEX",
    grandeur_metier="CONS",
    grandeur_physique="EA",
    type_calendrier="D",
    code_classe_temporelle="HPH",
    libelle_classe_temporelle="Heures Pleines Hiver / Saison Haute",
    unite="Wh",
    mesures_xml="",
) -> str:
    """Build a <serieMesuresDatees> XML fragment."""
    return f"""\
<serieMesuresDatees>
  <prmId>{prm_id}</prmId>
  <type>{type_mesure}</type>
  <grandeurMetier>{grandeur_metier}</grandeurMetier>
  <grandeurPhysique>{grandeur_physique}</grandeurPhysique>
  <typeCalendrier>{type_calendrier}</typeCalendrier>
  <codeClasseTemporelle>{code_classe_temporelle}</codeClasseTemporelle>
  <libelleClasseTemporelle>{libelle_classe_temporelle}</libelleClasseTemporelle>
  <unite>{unite}</unite>
  <mesuresDateesListe>
    {mesures_xml}
  </mesuresDateesListe>
</serieMesuresDatees>"""


def _make_r171_xml(
    emetteur="Enedis",
    destinataire="GRD-F121",
    date_heure_creation="2026-03-01T01:13:01",
    flux="R171",
    version="1.0",
    series_xml="",
    namespace=True,
) -> bytes:
    """Build a minimal valid R171 XML document."""
    ns_attr = ' xmlns:ns2="http://www.enedis.fr/stm/R171"' if namespace else ""
    root_open = f"<ns2:R171{ns_attr}>" if namespace else "<R171>"
    root_close = "</ns2:R171>" if namespace else "</R171>"
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
{root_open}
  <entete>
    <emetteur>{emetteur}</emetteur>
    <destinataire>{destinataire}</destinataire>
    <dateHeureCreation>{date_heure_creation}</dateHeureCreation>
    <flux>{flux}</flux>
    <version>{version}</version>
  </entete>
  <serieMesuresDateesListe>
    {series_xml}
  </serieMesuresDateesListe>
{root_close}""".encode("utf-8")


# ---------------------------------------------------------------------------
# Tests — Nominal parsing
# ---------------------------------------------------------------------------


class TestParseR171Nominal:
    def test_parsing_nominal(self):
        """XML with one serie + one mesure -> all fields extracted correctly."""
        mesure = _make_mesure_xml("2026-03-01T00:51:11", "1320")
        serie = _make_serie_xml(mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        assert isinstance(result, ParsedR171File)
        assert len(result.series) == 1

        s = result.series[0]
        assert s.point_id == "30000550506121"
        assert s.type_mesure == "INDEX"
        assert s.grandeur_metier == "CONS"
        assert s.grandeur_physique == "EA"
        assert s.type_calendrier == "D"
        assert s.code_classe_temporelle == "HPH"
        assert s.libelle_classe_temporelle == "Heures Pleines Hiver / Saison Haute"
        assert s.unite == "Wh"
        assert len(s.mesures) == 1

        m = s.mesures[0]
        assert m.date_fin == "2026-03-01T00:51:11"
        assert m.valeur == "1320"

    def test_values_are_raw_strings(self):
        """All values remain strings — no int/float/datetime conversion."""
        mesure = _make_mesure_xml("2026-03-01T00:51:11", "1320")
        serie = _make_serie_xml(mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        s = result.series[0]
        assert isinstance(s.point_id, str)
        assert isinstance(s.type_mesure, str)
        assert isinstance(s.grandeur_metier, str)
        assert isinstance(s.grandeur_physique, str)
        assert isinstance(s.unite, str)

        m = s.mesures[0]
        assert isinstance(m.date_fin, str)
        assert isinstance(m.valeur, str)


# ---------------------------------------------------------------------------
# Tests — Multiple PRM / mesures
# ---------------------------------------------------------------------------


class TestParseR171MultipleSeries:
    def test_multiple_prm(self):
        """Multiple series with different PRMs -> mesures for each."""
        mesure1 = _make_mesure_xml("2026-03-01T00:00:00", "100")
        mesure2 = _make_mesure_xml("2026-03-01T00:00:00", "200")
        serie1 = _make_serie_xml(prm_id="30000550506121", mesures_xml=mesure1)
        serie2 = _make_serie_xml(prm_id="30000550506999", mesures_xml=mesure2)
        xml = _make_r171_xml(series_xml=serie1 + serie2)
        result = parse_r171(xml)

        assert len(result.series) == 2
        assert result.series[0].point_id == "30000550506121"
        assert result.series[0].mesures[0].valeur == "100"
        assert result.series[1].point_id == "30000550506999"
        assert result.series[1].mesures[0].valeur == "200"

    def test_multiple_mesures_per_serie(self):
        """Serie with N mesureDatee entries -> all extracted."""
        mesures = "\n".join(
            [
                _make_mesure_xml("2026-03-01T00:00:00", "100"),
                _make_mesure_xml("2026-03-01T01:00:00", "200"),
                _make_mesure_xml("2026-03-01T02:00:00", "300"),
            ]
        )
        serie = _make_serie_xml(mesures_xml=mesures)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        assert len(result.series[0].mesures) == 3
        assert result.series[0].mesures[0].valeur == "100"
        assert result.series[0].mesures[1].valeur == "200"
        assert result.series[0].mesures[2].valeur == "300"

    def test_total_measures_across_series(self):
        mesure1 = "\n".join(
            [
                _make_mesure_xml("2026-03-01T00:00:00", "100"),
                _make_mesure_xml("2026-03-01T01:00:00", "200"),
            ]
        )
        mesure2 = _make_mesure_xml("2026-03-01T00:00:00", "300")
        serie1 = _make_serie_xml(prm_id="30000550506121", mesures_xml=mesure1)
        serie2 = _make_serie_xml(prm_id="30000550506999", mesures_xml=mesure2)
        xml = _make_r171_xml(series_xml=serie1 + serie2)
        result = parse_r171(xml)

        assert result.total_measures == 3


# ---------------------------------------------------------------------------
# Tests — Header parsing
# ---------------------------------------------------------------------------


class TestParseR171Header:
    def test_header_fields_in_raw_dict(self):
        """All entete fields appear in raw dict."""
        xml = _make_r171_xml(
            emetteur="Enedis",
            destinataire="GRD-F121",
            date_heure_creation="2026-03-01T01:13:01",
            flux="R171",
            version="1.0",
        )
        result = parse_r171(xml)

        raw = result.header.raw
        assert raw["emetteur"] == "Enedis"
        assert raw["destinataire"] == "GRD-F121"
        assert raw["dateHeureCreation"] == "2026-03-01T01:13:01"
        assert raw["flux"] == "R171"
        assert raw["version"] == "1.0"


# ---------------------------------------------------------------------------
# Tests — Namespace tolerance
# ---------------------------------------------------------------------------


class TestParseR171Namespace:
    def test_with_namespace(self):
        """XML with ns2 namespace -> same result."""
        mesure = _make_mesure_xml("2026-03-01T00:51:11", "1320")
        serie = _make_serie_xml(mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie, namespace=True)
        result = parse_r171(xml)

        assert len(result.series) == 1
        assert result.series[0].point_id == "30000550506121"

    def test_without_namespace(self):
        """XML without ns2 namespace -> same result."""
        mesure = _make_mesure_xml("2026-03-01T00:51:11", "1320")
        serie = _make_serie_xml(mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie, namespace=False)
        result = parse_r171(xml)

        assert len(result.series) == 1
        assert result.series[0].point_id == "30000550506121"

    def test_namespace_tolerance_same_result(self):
        """With and without namespace produce identical data."""
        mesure = _make_mesure_xml("2026-03-01T00:51:11", "1320")
        serie = _make_serie_xml(mesures_xml=mesure)

        result_ns = parse_r171(_make_r171_xml(series_xml=serie, namespace=True))
        result_no_ns = parse_r171(_make_r171_xml(series_xml=serie, namespace=False))

        assert result_ns.series[0].point_id == result_no_ns.series[0].point_id
        assert result_ns.series[0].mesures[0].valeur == result_no_ns.series[0].mesures[0].valeur
        assert result_ns.header.raw["flux"] == result_no_ns.header.raw["flux"]


# ---------------------------------------------------------------------------
# Tests — Edge cases (empty)
# ---------------------------------------------------------------------------


class TestParseR171Empty:
    def test_empty_series_list(self):
        """0 series -> no error, total_measures=0."""
        xml = _make_r171_xml(series_xml="")
        result = parse_r171(xml)

        assert len(result.series) == 0
        assert result.total_measures == 0

    def test_empty_mesures_in_serie(self):
        """Serie with 0 mesureDatee -> empty list, no error."""
        serie = _make_serie_xml(mesures_xml="")
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        assert len(result.series) == 1
        assert len(result.series[0].mesures) == 0

    def test_valeur_absent_is_none(self):
        """mesureDatee without <valeur> -> valeur is None."""
        mesure = _make_mesure_xml("2026-03-01T00:00:00")  # no valeur
        serie = _make_serie_xml(mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        assert result.series[0].mesures[0].valeur is None


# ---------------------------------------------------------------------------
# Tests — Error handling
# ---------------------------------------------------------------------------


class TestParseR171Errors:
    def test_invalid_xml_raises(self):
        with pytest.raises(R171ParseError, match="Invalid XML"):
            parse_r171(b"not xml at all")

    def test_wrong_root_tag_raises(self):
        xml = b'<?xml version="1.0"?><NotR171/>'
        with pytest.raises(R171ParseError, match="Expected root <R171>"):
            parse_r171(xml)

    def test_missing_entete_raises(self):
        xml = b"""\
<?xml version="1.0"?><R171>
<serieMesuresDateesListe></serieMesuresDateesListe>
</R171>"""
        with pytest.raises(R171ParseError, match="Missing <entete>"):
            parse_r171(xml)

    def test_missing_series_liste_raises(self):
        xml = b"""\
<?xml version="1.0"?><R171>
<entete><flux>R171</flux></entete>
</R171>"""
        with pytest.raises(R171ParseError, match="Missing <serieMesuresDateesListe>"):
            parse_r171(xml)

    def test_missing_prm_id_raises(self):
        """serieMesuresDatees without prmId -> R171ParseError."""
        serie_xml = """\
<serieMesuresDatees>
  <type>INDEX</type>
  <mesuresDateesListe></mesuresDateesListe>
</serieMesuresDatees>"""
        xml = _make_r171_xml(series_xml=serie_xml)
        with pytest.raises(R171ParseError, match="Missing or empty <prmId>"):
            parse_r171(xml)

    def test_empty_prm_id_raises(self):
        """serieMesuresDatees with whitespace-only prmId -> R171ParseError."""
        serie_xml = """\
<serieMesuresDatees>
  <prmId>  </prmId>
  <type>INDEX</type>
  <mesuresDateesListe></mesuresDateesListe>
</serieMesuresDatees>"""
        xml = _make_r171_xml(series_xml=serie_xml)
        with pytest.raises(R171ParseError, match="Missing or empty <prmId>"):
            parse_r171(xml)

    def test_missing_date_fin_raises(self):
        """mesureDatee without dateFin -> R171ParseError."""
        mesure_xml = "<mesureDatee><valeur>100</valeur></mesureDatee>"
        serie = _make_serie_xml(mesures_xml=mesure_xml)
        xml = _make_r171_xml(series_xml=serie)
        with pytest.raises(R171ParseError, match="Missing or empty <dateFin>"):
            parse_r171(xml)


# ---------------------------------------------------------------------------
# Tests — Whitespace stripping
# ---------------------------------------------------------------------------


class TestParseR171Whitespace:
    def test_whitespace_in_fields_stripped(self):
        """Leading/trailing whitespace in XML text is stripped."""
        mesure = "<mesureDatee><dateFin>  2026-03-01T00:51:11  </dateFin><valeur>  1320  </valeur></mesureDatee>"
        serie = _make_serie_xml(mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        m = result.series[0].mesures[0]
        assert m.date_fin == "2026-03-01T00:51:11"
        assert m.valeur == "1320"


# ---------------------------------------------------------------------------
# Tests — Grandeur physique variants
# ---------------------------------------------------------------------------


class TestParseR171GrandeurPhysique:
    @pytest.mark.parametrize("gp", ["DD", "DQ", "EA", "ERC", "ERI", "PMA", "TF"])
    def test_all_grandeur_physique_variants(self, gp):
        """All documented grandeur_physique values are accepted."""
        mesure = _make_mesure_xml("2026-03-01T00:00:00", "100")
        serie = _make_serie_xml(grandeur_physique=gp, mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        assert result.series[0].grandeur_physique == gp


# ---------------------------------------------------------------------------
# Tests — Classes temporelles
# ---------------------------------------------------------------------------


class TestParseR171ClasseTemporelle:
    @pytest.mark.parametrize("ct", ["HCE", "HCH", "HPE", "HPH", "P"])
    def test_all_classes_temporelles(self, ct):
        """All documented classe temporelle codes are accepted."""
        mesure = _make_mesure_xml("2026-03-01T00:00:00", "100")
        serie = _make_serie_xml(code_classe_temporelle=ct, mesures_xml=mesure)
        xml = _make_r171_xml(series_xml=serie)
        result = parse_r171(xml)

        assert result.series[0].code_classe_temporelle == ct
