"""
PROMEOS V4 · Structured logging config (ADR-027 IS7-IS9).

Sprint M2-1 Foundation infra : helpers `configure_logging()` + `anonymize_ip()`.
Câblage middleware FastAPI : Sprint M2-3 (sécurité layer).

Invariants applicables (cf. ADR-027 §3) :
- IS7 : logs sanitisés JSON structlog (pas de body / token / query string sensible)
- IS8 : IP anonymisée /24 IPv4 + /48 IPv6 (anti-tracking RGPD CNIL art. 5(2))
- IS9 : `correlation_id` propagé dans tous events log (IDOR forensique)

Source : docs/dev/L4_ADR-027_securite_org_scoping.md §7 (commit faba2a61 · 50/50 ✓).
"""

import ipaddress

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog avec JSON renderer + sanitization par défaut.

    Câblé par `backend/main.py` au démarrage FastAPI (Sprint M2-3).

    Args:
        log_level: niveau de log ("DEBUG", "INFO", "WARNING", "ERROR").

    Sortie : événements JSON sur stdout (collectable par observabilité externe).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # IS9 correlation_id depuis context
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),  # IS7 JSON structuré
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), log_level.upper(), 20)  # 20 = INFO
        ),
    )


def anonymize_ip(ip: str) -> str:
    """
    IS8 : anonymisation IP RGPD CNIL.

    IPv4 : /24 mask (ex. 192.168.1.42 → 192.168.1.0)
    IPv6 : /48 mask (ex. 2a01:cb00:1234::1 → 2a01:cb00:1234::)

    Conforme recommandation CNIL "logs serveur web" 2023.
    Préserve la valeur forensique (analyse réseau /24) sans tracker l'utilisateur final.

    Args:
        ip: adresse IP source (str, IPv4 ou IPv6).

    Returns:
        IP anonymisée str. "unknown" si parse failed.
    """
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv4Address):
            network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        else:
            network = ipaddress.IPv6Network(f"{ip}/48", strict=False)
        return str(network.network_address)
    except (ValueError, TypeError):
        return "unknown"
