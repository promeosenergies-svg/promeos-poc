"""
PROMEOS - Tests Hub Page L11 : GET /api/cockpit/jour
Phase L11 grammaire v1.2 — CockpitJourPayload (hero + 3 KPIs + 2 charts +
3 highlights différenciés + footer SCM).

Source-guards :
  - L11.1 : exactement 3 KPIs
  - L11.2 : exactement 2 charts
  - L11.3 : 3-5 highlights diversifiés (anti-pattern AP3)
  - L11.4 : verbes d'invitation tous dans ALLOWED_VERBS
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app

ALLOWED_VERBS = {
    "voir",
    "lancer",
    "comparer",
    "auditer",
    "ouvrir",
    "vérifier",
    "simuler",
    "arbitrer",
    "programmer",
    "activer",
    "préparer",
    "contester",
}


@pytest.fixture
def client():
    """Client avec la DB demo (tests read-only)."""
    return TestClient(app)


# ── L11.0 : Endpoint accessible ──────────────────────────────────────────


def test_endpoint_exists(client):
    """GET /api/cockpit/jour doit retourner HTTP 200."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    assert r.status_code == 200, f"Statut inattendu {r.status_code}: {r.text[:200]}"


def test_endpoint_returns_json(client):
    """La réponse est du JSON valide."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    assert r.headers["content-type"].startswith("application/json")
    _ = r.json()  # ne doit pas lever


# ── L11.1 : Structure payload ─────────────────────────────────────────────


def test_payload_structure_l11(client):
    """Payload contient hero + kpis (3) + charts (2) + highlights (3-5) + footer."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    d = r.json()
    assert "hero" in d, "Clé 'hero' absente"
    assert len(d["kpis"]) == 3, "L11.1 : exactement 3 KPIs requis"
    assert len(d["charts"]) == 2, "L11.2 : exactement 2 charts requis"
    assert 3 <= len(d["highlights"]) <= 5, "L11.3 : 3-5 highlights requis"
    assert "footer" in d, "Clé 'footer' absente"


# ── L11.2 : Hero block ────────────────────────────────────────────────────


def test_hero_has_required_fields(client):
    """Hero doit contenir eyebrow, title, sub, meta, alerts."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    hero = r.json()["hero"]
    for field in ("eyebrow", "title", "sub", "meta", "alerts"):
        assert field in hero, f"Champ hero.{field} manquant"


def test_hero_meta_has_quality_and_confidence(client):
    """hero.meta doit avoir quality (int) + confidence (str) + period + scope."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    meta = r.json()["hero"]["meta"]
    assert isinstance(meta.get("quality"), int), "meta.quality doit être entier"
    assert meta.get("confidence") in ("high", "medium", "low"), "meta.confidence invalide"
    assert "period" in meta
    assert "scope" in meta


def test_hero_alerts_structure(client):
    """hero.alerts contient count et criticalCount (entiers >= 0)."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    alerts = r.json()["hero"]["alerts"]
    assert isinstance(alerts.get("count"), int) and alerts["count"] >= 0
    assert isinstance(alerts.get("criticalCount"), int) and alerts["criticalCount"] >= 0


# ── L11.3 : KPIs ─────────────────────────────────────────────────────────


def test_kpis_have_id_label_value_unit(client):
    """Chaque KPI doit exposer id, eyebrow, label, value, unit."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for i, kpi in enumerate(r.json()["kpis"]):
        for field in ("id", "eyebrow", "label", "value", "unit"):
            assert field in kpi, f"kpis[{i}].{field} manquant"


def test_kpis_value_is_numeric(client):
    """kpi.value doit être numérique (int ou float)."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for kpi in r.json()["kpis"]:
        assert isinstance(kpi["value"], (int, float)), f"kpi '{kpi['id']}' value non numérique"


def test_kpis_delta_direction_valid(client):
    """kpi.delta.direction ∈ {up, down, stable} si présent."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for kpi in r.json()["kpis"]:
        delta = kpi.get("delta")
        if delta:
            assert delta.get("direction") in ("up", "down", "stable"), f"kpi '{kpi['id']}' delta.direction invalide"


def test_kpis_ids_are_unique(client):
    """Les 3 KPI IDs doivent être distincts."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    ids = [k["id"] for k in r.json()["kpis"]]
    assert len(ids) == len(set(ids)), f"IDs KPI dupliqués : {ids}"


# ── L11.4 : Charts ───────────────────────────────────────────────────────


def test_charts_have_id_type_question_answer(client):
    """Chaque chart doit avoir id, type, question, answer."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for i, chart in enumerate(r.json()["charts"]):
        for field in ("id", "type", "question", "answer"):
            assert field in chart, f"charts[{i}].{field} manquant"


def test_chart_bars_has_series(client):
    """Le chart bar_daily_7d doit avoir une série non-vide."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    bars = next((c for c in r.json()["charts"] if c["type"] == "bar_daily_7d"), None)
    assert bars is not None, "Chart bar_daily_7d absent"
    assert len(bars.get("series", [])) > 0, "Series vide pour bar_daily_7d"


def test_chart_line_has_subscribed_kw(client):
    """Le chart line_24h_hp_hc doit exposer subscribed_kw (numérique > 0)."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    line = next((c for c in r.json()["charts"] if c["type"] == "line_24h_hp_hc"), None)
    assert line is not None, "Chart line_24h_hp_hc absent"
    assert isinstance(line.get("subscribed_kw"), (int, float)) and line["subscribed_kw"] > 0


# ── L11.5 : Highlights — anti-pattern AP3 ────────────────────────────────


def test_highlights_differenciated_l11_3(client):
    """Anti-pattern AP3 : 4× même catégorie INTERDIT (min 2 catégories distinctes)."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    cats = {h["category"] for h in r.json()["highlights"]}
    assert len(cats) >= 2, f"Anti-pattern AP3 : catégories trop homogènes → {cats}"


def test_highlights_have_invitation_verb(client):
    """L11.3 : tout highlight DOIT avoir un verbe d'invitation autorisé."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for h in r.json()["highlights"]:
        verb = h["invitation"]["verb"]
        assert verb in ALLOWED_VERBS, f"Verbe '{verb}' non autorisé (L11.3)"


def test_highlights_have_required_fields(client):
    """Chaque highlight a id, rang, severity, category, scope, title, evidence, invitation."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for i, h in enumerate(r.json()["highlights"]):
        for field in ("id", "rang", "severity", "category", "scope", "title", "evidence", "invitation"):
            assert field in h, f"highlights[{i}].{field} manquant"


def test_highlights_severity_values(client):
    """highlight.severity ∈ {crit, warn, info}."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for h in r.json()["highlights"]:
        assert h["severity"] in ("crit", "warn", "info"), f"highlight '{h['id']}' severity='{h['severity']}' invalide"


def test_highlights_rang_ascending(client):
    """Les rangs highlights doivent être distincts et >= 1."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    rangs = [h["rang"] for h in r.json()["highlights"]]
    assert len(rangs) == len(set(rangs)), f"Rangs dupliqués : {rangs}"
    assert all(r >= 1 for r in rangs), f"Rang < 1 détecté : {rangs}"


# ── L11.6 : Footer SCM ───────────────────────────────────────────────────


def test_footer_has_sources_confidence_updated(client):
    """Footer doit avoir sources (list), confidence, updatedAt, methodologyHref."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    footer = r.json()["footer"]
    assert isinstance(footer.get("sources"), list) and len(footer["sources"]) > 0
    assert footer.get("confidence") in ("high", "medium", "low")
    assert "updatedAt" in footer
    assert "methodologyHref" in footer


def test_footer_sources_have_label_and_type(client):
    """Chaque source footer a label + type."""
    r = client.get("/api/cockpit/jour", headers={"X-Org-Id": "1"})
    for i, src in enumerate(r.json()["footer"]["sources"]):
        assert "label" in src, f"footer.sources[{i}].label manquant"
        assert "type" in src, f"footer.sources[{i}].type manquant"


# ── L11.7 : Query params ─────────────────────────────────────────────────


def test_period_type_day_returns_200(client):
    """period_type=day doit fonctionner."""
    r = client.get("/api/cockpit/jour?period_type=day", headers={"X-Org-Id": "1"})
    assert r.status_code == 200


def test_period_type_month_returns_200(client):
    """period_type=month doit fonctionner."""
    r = client.get("/api/cockpit/jour?period_type=month", headers={"X-Org-Id": "1"})
    assert r.status_code == 200


def test_period_type_year_returns_200(client):
    """period_type=year doit fonctionner."""
    r = client.get("/api/cockpit/jour?period_type=year", headers={"X-Org-Id": "1"})
    assert r.status_code == 200
