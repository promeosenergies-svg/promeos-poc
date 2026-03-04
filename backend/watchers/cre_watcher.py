"""
PROMEOS Watchers - CRE (Commission de Regulation de l'Energie)
"""

from .rss_watcher import RSSWatcher


class CREWatcher(RSSWatcher):
    name = "cre"
    description = "CRE - Communiques et deliberations"
    source_url = "https://www.cre.fr/"
    rss_url = "https://www.cre.fr/rss/actualites.xml"  # Example URL (may need update)
    tags_default = "cre,energy,regulatory"
