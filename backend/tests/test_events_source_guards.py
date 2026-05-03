"""PROMEOS — Source guards Phase 1.A — Events REST endpoint.

Garde-fous statiques (lecture source) sur le nouvel endpoint
GET /api/v1/events/upcoming + couche query d'adaptation Voie C.

SG_EVENTS_01 : EventUpcomingResponse exclut tout champ monétaire brut
               au top-level (les € restent dans EventCardSchema.impact
               où ils sont contextualisés par period+mitigation).
SG_EVENTS_02 : endpoint délègue à events_query_service (aucune logique
               métier ni SQLAlchemy inline dans le handler).
SG_EVENTS_03 : org_id propagé via helper canonique multi-tenant
               (resolve_org_id ou _get_org_id, V57 SoT).
SG_EVENTS_04 : pas de seuils hardcoded (regex sur valeurs sentinelles
               connues 7500/0.052/etc.).
SG_EVENTS_05 : events_query_service ne mute pas event_bus/* (imports
               restreints à compute_events + types).

Ref : docs/audits/sprint_alpha_phase0_audit_20260502.md (Voie C),
docs/adr/ADR-002-chantier-alpha-moteur-evenements.md.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SCHEMA_PATH = os.path.join(_BACKEND_ROOT, "schemas", "events.py")
_SERVICE_PATH = os.path.join(_BACKEND_ROOT, "services", "events_query_service.py")
_ROUTE_PATH = os.path.join(_BACKEND_ROOT, "routes", "events.py")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestEventsSourceGuards:
    def test_sg_events_01_no_monetary_top_level_in_response(self):
        """SG_EVENTS_01 : EventUpcomingResponse n'expose pas de champ
        monétaire au top-level. Les €/EUR restent dans
        EventCardSchema.impact où ils sont contextualisés par period."""
        from schemas.events import EventUpcomingResponse

        fields = EventUpcomingResponse.model_fields
        for name in fields:
            lower = name.lower()
            assert "_eur" not in lower, f"Champ monétaire top-level interdit : {name}"
            assert "_amount" not in lower, f"Champ monétaire top-level interdit : {name}"
            assert "_euro" not in lower, f"Champ monétaire top-level interdit : {name}"
            assert "€" not in name, f"Symbole € interdit dans field name : {name}"

    def test_sg_events_02_endpoint_delegates_to_query_service(self):
        """SG_EVENTS_02 : le handler délègue à events_query_service —
        aucune query SQLAlchemy ni logique métier inline."""
        import inspect

        from routes.events import get_upcoming_events_endpoint

        body = inspect.getsource(get_upcoming_events_endpoint)

        forbidden = (
            "db.query(",
            ".filter(",
            ".count()",
            ".all()",
            ".scalar()",
            ".first()",
        )
        for token in forbidden:
            assert token not in body, (
                f"Handler events.py contient un appel SQL inline : {token!r}. "
                "La logique d'accès données doit rester dans event_bus / "
                "events_query_service."
            )

        # Doit appeler get_upcoming_events
        assert "get_upcoming_events(" in body, "Handler doit déléguer à events_query_service.get_upcoming_events"

    def test_sg_events_03_org_id_via_canonical_helper(self):
        """SG_EVENTS_03 : org_id résolu via helper canonique multi-tenant
        (resolve_org_id V57 SoT ou _get_org_id wrapper)."""
        src = _read(_ROUTE_PATH)

        # Au moins un des helpers canoniques doit être présent
        helpers = ("resolve_org_id", "_get_org_id")
        assert any(h in src for h in helpers), (
            "Aucun helper canonique multi-tenant détecté dans routes/events.py "
            f"(attendu : un de {helpers}). Risque de leak inter-org."
        )

        # Le handler doit appeler le helper avec request + auth
        assert "resolve_org_id(request, auth, db)" in src or "_get_org_id(request, auth" in src, (
            "L'appel au helper org_id doit propager request + auth"
        )

    def test_sg_events_04_no_hardcoded_thresholds(self):
        """SG_EVENTS_04 : aucune constante magique (seuils €, CO₂, BACS,
        prix, etc.) dans les 3 fichiers du chantier P1.A."""
        forbidden_values = {
            "7500",  # DT_PENALTY_EUR
            "3750",  # DT_PENALTY_AT_RISK_EUR
            "1500",  # APER_PARKING_MIN / BACS_PENALTY / OPERAT_PENALTY
            "0.052",  # CO2 elec
            "0.227",  # CO2 gaz
            "0.02658",  # accise legacy
            "0.068",  # PRICE_FALLBACK
            "8.50",  # CEE prix MWhc cumac (cf. cee-p6 skill)
        }
        for path in (_SCHEMA_PATH, _SERVICE_PATH, _ROUTE_PATH):
            src = _read(path)
            # Strip docstrings (triple-quoted) pour éviter faux positifs
            src_no_docstring = re.sub(r'"""[\s\S]*?"""', "", src, flags=re.MULTILINE)
            for value in forbidden_values:
                assert value not in src_no_docstring, (
                    f"Valeur hardcoded suspecte {value!r} détectée dans "
                    f"{os.path.basename(path)}. Router via doctrine/constants.py "
                    "ou config canonique."
                )

    def test_sg_events_05_query_service_does_not_mutate_event_bus(self):
        """SG_EVENTS_05 : events_query_service ne doit importer que
        compute_events + types depuis event_bus/. Aucun import d'autre
        symbole (qui suggérerait une mutation/extension du moteur)."""
        src = _read(_SERVICE_PATH)

        # Tous les imports `from services.event_bus(.X)? import Y`
        imports = re.findall(
            r"^from\s+services\.event_bus(\.[a-z_]+)?\s+import\s+([^\n]+)",
            src,
            flags=re.MULTILINE,
        )
        assert imports, "events_query_service doit importer event_bus (sinon que fait-il ?)"

        allowed_symbols = {
            "compute_events",
            "SolEventCard",
            "to_narrative_week_cards",  # toléré si transition douce
        }
        for submodule, symbols_str in imports:
            symbols = {s.strip() for s in symbols_str.split(",") if s.strip()}
            forbidden = symbols - allowed_symbols
            assert not forbidden, (
                f"Imports event_bus interdits dans events_query_service : "
                f"{forbidden}. Voie C exige réutilisation pure (compute_events + "
                f"types uniquement)."
            )

        # Aucune écriture / mutation directe sur event_bus
        assert (
            "event_bus.detectors" not in src or "import" in src.split("event_bus.detectors")[0].splitlines()[-1]
            if "event_bus.detectors" in src
            else True
        )
        # Pas de modification du DETECTORS registry
        assert "DETECTORS.append" not in src
        assert "DETECTORS.extend" not in src
        assert "DETECTORS[" not in src

    def test_sg_events_06_refresh_uses_strict_platform_admin(self):
        """SG_EVENTS_06 : POST /refresh utilise `require_platform_admin`
        (strict, pas de bypass DEMO_MODE).

        Q4 audit Phase 0.bis arbitrée : sécurité prod prime sur confort
        dev. Le cron GitHub Actions utilise un secret token réel admin,
        pas de bypass DEMO_MODE nécessaire.

        Garde-fou anti-régression : si quelqu'un remplace par
        `require_admin()` (lenient) ou `get_optional_auth`, ce test
        échoue avant le merge.
        """
        import inspect

        from routes.events import refresh_events_endpoint

        body = inspect.getsource(refresh_events_endpoint)

        # Doit utiliser le strict
        assert "require_platform_admin" in body, (
            "POST /refresh doit utiliser `require_platform_admin` "
            "(strict, pas de bypass DEMO_MODE) — cf. Q4 audit Phase 0.bis."
        )

        # NE doit PAS utiliser les variantes lenient
        # Note: `require_platform_admin` contient `require_admin` en sous-chaîne.
        # On checke `require_admin(` (avec parenthèse) ou `require_admin)` qui
        # ne match pas `require_platform_admin`.
        for forbidden in ("require_admin()", "Depends(require_admin)", "get_optional_auth"):
            assert forbidden not in body, f"POST /refresh ne doit pas utiliser {forbidden!r} (auth lenient/bypass)"
