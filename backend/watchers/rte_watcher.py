"""
PROMEOS Watchers - RTE (Reseau de Transport d'Electricite)
"""

from .rss_watcher import RSSWatcher


class RTEWatcher(RSSWatcher):
    name = "rte"
    description = "RTE - Actualites reseau electrique"
    source_url = "https://www.rte-france.com/"
    rss_url = "https://www.rte-france.com/rss/actualites.xml"  # Example URL (may need update)
    tags_default = "rte,grid,energy"
