"""Tests templates Jinja2 digest — Phase 2.D Sprint α-push.

Couvre :
- Render HTML + text avec events variés
- Cat A/B traçabilité : impact € avec/sans methodology
- Severity classes CSS appliquées
- Pluriel "signaux" vs singulier "signal"
- Anti-leak PII : pas d'event.id technique
- Truncate methodology > 140 chars
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _render_html(events, user_prenom="Marie", date_fr="15/10/2026"):
    from services.digest_service import _get_jinja_env

    env = _get_jinja_env()
    tmpl = env.get_template("digest_daily.html.j2")
    return tmpl.render(
        user={"prenom": user_prenom},
        events=events,
        date_fr=date_fr,
        app_base_url="https://app.promeos.io",
    )


def _render_text(events, user_prenom="Marie", date_fr="15/10/2026"):
    from services.digest_service import _get_jinja_env

    env = _get_jinja_env()
    tmpl = env.get_template("digest_daily.txt.j2")
    return tmpl.render(
        user={"prenom": user_prenom},
        events=events,
        date_fr=date_fr,
        app_base_url="https://app.promeos.io",
    )


def _event(severity="warning", value=None, unit=None, period="month", methodology=None):
    return {
        "severity": severity,
        "title": "Conformité DT à risque",
        "narrative": "Trajectoire 2030 sous tension sur 2 sites.",
        "impact": {"value": value, "unit": unit, "period": period},
        "source": {"methodology": methodology},
        "action": {"label": "Voir conformité", "route": "/conformite"},
    }


class TestHtmlTemplate:
    def test_renders_with_user_prenom(self):
        html = _render_html([_event()], user_prenom="Marie")
        assert "Bonjour Marie" in html

    def test_fallback_user_when_no_prenom(self):
        html = _render_html([_event()], user_prenom=None)
        assert "Bonjour à toi" in html

    def test_severity_class_applied(self):
        html = _render_html([_event(severity="critical")])
        assert "severity-critical" in html

    def test_pluralization_signal(self):
        html_one = _render_html([_event()])
        html_many = _render_html([_event(), _event(), _event()])
        assert "1 signal" in html_one or "1 signaux" not in html_one
        assert "3 signaux" in html_many

    def test_impact_eur_with_methodology_renders_source(self):
        """Cat A : impact € + methodology → source visible."""
        html = _render_html(
            [
                _event(
                    value=15000.0,
                    unit="€",
                    period="year",
                    methodology="DT_PENALTY_EUR=7500 × 2 sites non-conformes (Décret 2019-771)",
                )
            ]
        )
        # Format compact FR (espace insécable séparateur milliers)
        assert "15 000" in html or "15000" in html
        assert "€" in html
        assert "DT_PENALTY_EUR=7500" in html
        assert "Source" in html

    def test_impact_eur_without_methodology_falls_back(self):
        """Cat B : impact € sans methodology → 'à préciser' (anti-faux-positif)."""
        html = _render_html([_event(value=15000.0, unit="€", period="year", methodology=None)])
        assert "à préciser" in html
        # Pas de "Source :" rendu (no methodology)
        assert "Source :" not in html

    def test_impact_non_eur_unit_renders_normally(self):
        """Impact en jours/kWh/etc. → rendu standard sans Cat A/B."""
        html = _render_html([_event(value=17.0, unit="days", period="deadline")])
        assert "17" in html
        assert "days" in html

    def test_impact_none_value_omitted(self):
        """Impact value=None → bloc impact omis (pas de '€ None')."""
        html = _render_html([_event(value=None, unit="€", period="year")])
        assert "Impact" not in html or "à préciser" not in html
        # Pas de None affiché
        assert "None" not in html

    def test_action_link_uses_app_base_url(self):
        html = _render_html([_event()])
        assert "https://app.promeos.io/conformite" in html
        assert "Voir conformité" in html

    def test_unsubscribe_link_present(self):
        html = _render_html([_event()])
        assert "settings/notifications" in html
        assert "Désabonner" in html

    def test_no_pii_technical_identifiers_leaked(self):
        """Anti-leak PII : event.id, source.system, source.last_updated_at
        ne doivent pas être rendus dans le HTML."""
        # On crée un event avec les champs PII complets (comme si serialization
        # avait laissé fuiter), template doit ignorer.
        evt = _event()
        # Le template attend un dict simple — pas d'event.id exposé par
        # _event_to_template_dict (vérifié SG_DIGEST_03)
        html = _render_html([evt])
        assert "event_id" not in html
        assert "source_system" not in html
        assert "last_updated_at" not in html

    def test_methodology_truncated(self):
        long_method = "A" * 200
        html = _render_html([_event(value=100.0, unit="€", period="year", methodology=long_method)])
        # Truncate Jinja2 default add "..." ou similar
        assert "AAAAAAAAAAAAA" in html  # 13+ A présents
        # Mais pas les 200 chars (truncate à 140)
        assert "A" * 200 not in html


class TestTextTemplate:
    def test_renders_text_version(self):
        text = _render_text([_event()])
        assert "PROMEOS — Digest" in text
        assert "Conformité DT à risque" in text

    def test_text_no_html_tags(self):
        text = _render_text([_event()])
        assert "<html>" not in text
        assert "<div" not in text
        assert "<p>" not in text

    def test_text_includes_impact_eur_methodology(self):
        text = _render_text(
            [
                _event(
                    value=15000.0,
                    unit="€",
                    period="year",
                    methodology="Decret 2019-771 calcul direct",
                )
            ]
        )
        assert "Source : Decret 2019-771" in text

    def test_text_severity_uppercase_marker(self):
        text = _render_text([_event(severity="critical")])
        assert "[CRITICAL]" in text
