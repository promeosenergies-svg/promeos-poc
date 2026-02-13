"""
PROMEOS Watchers - Generic RSS watcher (stdlib only, no feedparser)
"""
import hashlib
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from models import RegSourceEvent, WatcherEventStatus
from .base import Watcher


def _normalize_dedup_key(title: str, published_date: str, source: str) -> str:
    """Normalize: lowercase, strip accents/punct, trim -> SHA256."""
    text = f"{title}|{published_date}|{source}"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9|]", "", text.lower())
    return hashlib.sha256(text.encode()).hexdigest()[:128]


class RSSWatcher(Watcher):
    """Base class pour watchers RSS utilisant xml.etree."""

    rss_url: str = ""
    tags_default: str = "regulatory"

    def check(self, db: Session) -> List[RegSourceEvent]:
        """Parse RSS feed et cree des RegSourceEvents (dedupliques par hash)."""
        events = []
        try:
            req = urllib.request.Request(self.rss_url, headers={"User-Agent": "PROMEOS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_content = response.read()

            root = ET.fromstring(xml_content)

            # Parse RSS 2.0 format
            for item in root.findall(".//item")[:10]:  # Max 10 items
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_date_elem = item.find("pubDate")

                if title_elem is None or title_elem.text is None:
                    continue

                title = title_elem.text.strip()
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else self.rss_url
                description = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                pub_date_str = pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else None

                # Create content hash
                content = f"{title}|{url}"
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                # Check if already exists
                existing = db.query(RegSourceEvent).filter(
                    RegSourceEvent.content_hash == content_hash
                ).first()

                if existing:
                    continue  # Skip duplicates

                # Create snippet (max 500 chars)
                snippet = (description[:500] + "...") if len(description) > 500 else description

                # Parse pub_date (best effort)
                published_at = None
                if pub_date_str:
                    try:
                        # Simple ISO format attempt
                        published_at = datetime.fromisoformat(pub_date_str.replace("Z", ""))
                    except:
                        pass

                # Compute normalized dedup key
                dedup_key = _normalize_dedup_key(
                    title, pub_date_str or "", self.name
                )

                event = RegSourceEvent(
                    source_name=self.name,
                    title=title,
                    url=url,
                    content_hash=content_hash,
                    snippet=snippet,
                    tags=self.tags_default,
                    published_at=published_at,
                    retrieved_at=datetime.utcnow(),
                    reviewed=False,
                    status=WatcherEventStatus.NEW,
                    dedup_key=dedup_key,
                )
                db.add(event)
                events.append(event)

            db.commit()
        except Exception as e:
            print(f"RSS watcher {self.name} error: {e}")

        return events
