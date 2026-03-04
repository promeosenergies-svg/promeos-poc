"""
PROMEOS Watchers - Legifrance JORF feed
"""

from .rss_watcher import RSSWatcher


class LegifranceWatcher(RSSWatcher):
    name = "legifrance"
    description = "Legifrance - Journal Officiel RF"
    source_url = "https://www.legifrance.gouv.fr/"
    rss_url = "https://www.legifrance.gouv.fr/jorf/rss"  # Flux JORF
    tags_default = "legifrance,jorf,regulatory"
