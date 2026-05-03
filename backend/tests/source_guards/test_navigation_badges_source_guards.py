"""PROMEOS — Source guards Phase 2.A — P1.2 navigation badges.

Garde-fous statiques (lecture source) sur le nouveau endpoint
GET /api/v1/navigation/badges et son service d'agrégation.

SG_NAV_01 : NavBadgesResponse exclut tout champ monétaire.
SG_NAV_02 : compute_navigation_badges délègue à des helpers privés
            (pas de query SQLAlchemy inline).
SG_NAV_03 : org_id propagé dans tous les helpers _count_*.
SG_NAV_04 : pas de hardcoded threshold (constantes SoT projet).

Audit ref : audit/navigation_audit_20260501.md §3.3 + §5.
"""

from __future__ import annotations

import os
import re
import sys

# Permet d'importer les modules backend depuis tests/ sans installer le
# package — convention partagée avec les autres source-guards du repo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "schemas",
    "navigation.py",
)
_SERVICE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "services",
    "navigation_badges_service.py",
)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestNavBadgesSourceGuards:
    def test_sg_nav_01_no_monetary_fields_in_response(self):
        """SG_NAV_01 : NavBadgesResponse ne doit pas exposer de monétaire.

        Les badges nav sont des compteurs ou pourcentages — l'argent (€,
        EUR, _amount) n'a sa place ni dans le contrat OpenAPI ni dans
        l'agrégation. Cf. doctrine §6.2 anti-pattern "menus muets".
        """
        from schemas.navigation import NavBadgesResponse

        fields = NavBadgesResponse.model_fields  # pydantic v2
        for name in fields:
            lower = name.lower()
            assert "_eur" not in lower, f"Champ monétaire interdit : {name}"
            assert "_amount" not in lower, f"Champ monétaire interdit : {name}"
            assert "_euro" not in lower, f"Champ monétaire interdit : {name}"
            assert "€" not in name, f"Champ monétaire interdit : {name}"

        # Code source du schema : aucune chaîne contenant € ni EUR.
        src = _read(_SCHEMA_PATH)
        assert "€" not in src, "€ détecté dans schemas/navigation.py"
        # Le terme 'EUR' isolé est interdit (autorise bien sûr les mots qui
        # le contiennent comme 'European' s'il en arrivait — non observé).
        assert not re.search(r"\bEUR\b", src), "EUR détecté dans schemas/navigation.py"

    def test_sg_nav_02_aggregator_delegates_to_helpers(self):
        """SG_NAV_02 : compute_navigation_badges ne doit pas faire de
        query SQLAlchemy inline. La fonction délègue à des helpers
        privés (`_count_*`) — toute query inline serait du dead-code
        métier réintroduit dans la couche d'agrégation.

        Implémentation robuste via inspect.getsource — le corps de la
        fonction est isolé indépendamment de l'ordre de déclaration
        dans le module (fix P2 reviewer Phase 2.A).
        """
        import inspect

        from services.navigation_badges_service import compute_navigation_badges

        body = inspect.getsource(compute_navigation_badges)

        # Aucune query SQLAlchemy inline ne doit apparaître dans le corps.
        forbidden = ("db.query(", ".filter(", ".count()", ".all()")
        for token in forbidden:
            assert token not in body, (
                f"compute_navigation_badges contient un appel SQLAlchemy "
                f"inline interdit : {token!r}. Extraire vers un helper "
                "privé _count_* dans le même module."
            )

    def test_sg_nav_03_org_id_propagated_to_all_helpers(self):
        """SG_NAV_03 : tous les helpers privés doivent recevoir org_id.

        Garantit l'isolation multi-tenant — un helper qui oublierait
        org_id leakerait potentiellement les données entre orgs.
        """
        src = _read(_SERVICE_PATH)

        # Liste tous les helpers privés (def _xxx(...))
        helpers = re.findall(r"^def (_[a-z_]+)\(([^)]*)\)", src, flags=re.MULTILINE)
        assert helpers, "aucun helper privé détecté — refacto incomplète ?"
        critical_helpers = {
            "_count_open_monitoring_alerts",
            "_count_unreviewed_billing_anomalies",
            "_count_market_windows_within",
            "_count_compliance_critical_warn",
            "_count_action_center_open",
            "_compute_compliance_progress",
            "_org_active_site_ids_subquery",
        }
        seen = {name for name, _ in helpers}
        missing = critical_helpers - seen
        assert not missing, f"Helpers privés manquants : {missing}"

        for name, signature in helpers:
            if name not in critical_helpers:
                continue
            assert "org_id" in signature, (
                f"Helper {name} ne reçoit pas org_id — risque de leak multi-tenant. Signature : ({signature})"
            )

    def test_sg_nav_05_count_summary_signature_stable(self):
        """SG_NAV_05 : signature stable de notification_service._count_summary.

        Mitigation du couplage cross-module sur un symbole privé (cf.
        commentaire navigation_badges_service.py:25-32). Si la signature
        ou les clés du dict retourné changent dans notification_service,
        ce test échoue avant que le couplage casse silencieusement.

        Garde-fou complémentaire à `test_org_isolation` (intégration).
        """
        import inspect

        from services.notification_service import _count_summary

        # Signature : (db, org_id, site_id=None) — minimum 2 paramètres
        # positionnels nommés `db` et `org_id`.
        sig = inspect.signature(_count_summary)
        params = list(sig.parameters.keys())
        assert params[0] == "db", f"_count_summary signature drifted : 1er param attendu 'db', trouvé '{params[0]}'"
        assert "org_id" in params, f"_count_summary doit recevoir 'org_id' — params actuels : {params}"

    def test_sg_nav_04_no_hardcoded_thresholds(self):
        """SG_NAV_04 : aucune constante magique (seuils CO₂, prix, BACS).

        Les compteurs nav sont une simple agrégation — toute constante
        métier doit venir d'une SoT (config_emission_factors, regs.yaml,
        catalog billing) et non être inline ici.
        """
        src = _read(_SERVICE_PATH)

        # Nettoyage : on ignore les commentaires, doctrings et le nom de
        # l'attribut PURCHASE_WINDOW_DAYS (constante locale documentée).
        # On ne flag que les VALEURS littérales suspectes hors contextes
        # autorisés.
        forbidden_values = {
            "7500",  # seuil DT m² (cf. regs.yaml)
            "0.052",  # facteur CO₂ élec (cf. emission_factors.py)
            "0.227",  # facteur CO₂ gaz
            "1.9",  # taux IPC fictif
        }

        for value in forbidden_values:
            # Match littéral, mais pas dans une chaîne de commentaire.
            # Heuristique simple : on vérifie l'absence sur le code "stripped".
            stripped = "\n".join(line.split("#", 1)[0] for line in src.splitlines() if not line.strip().startswith("#"))
            assert value not in stripped, (
                f"Constante magique '{value}' détectée dans navigation_badges_service.py — extraire vers SoT."
            )

        # PURCHASE_WINDOW_DAYS = 90 est documenté en commentaire au-dessus
        # comme aligné sur contract_expiration_alerts.py (convention prod).
        # On accepte cette valeur car elle a une SoT documentée.
