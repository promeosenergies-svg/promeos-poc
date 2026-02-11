"""
PROMEOS Referentiel — HTML to Markdown normalizer.
Strips navigation, scripts, styles. Keeps readable text.
"""
import re
from html.parser import HTMLParser
from typing import Optional


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text extractor without external deps."""

    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg", "iframe"}
    BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br", "hr",
                  "blockquote", "section", "article", "main", "table", "thead", "tbody"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0
        self._current_tag: Optional[str] = None

    def handle_starttag(self, tag: str, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip_depth += 1
        if self._skip_depth == 0:
            self._current_tag = tag_lower
            if tag_lower in self.BLOCK_TAGS:
                self._parts.append("\n")
            if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag_lower[1])
                self._parts.append("#" * level + " ")

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if self._skip_depth == 0 and tag_lower in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse whitespace but keep paragraph breaks
        lines = raw.split("\n")
        cleaned = []
        for line in lines:
            stripped = " ".join(line.split())
            if stripped:
                cleaned.append(stripped)
        text = "\n\n".join(cleaned)
        # Collapse 3+ newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_markdown(html_content: str) -> str:
    """Convert raw HTML to cleaned markdown-like text."""
    extractor = _TextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


def extract_title(html_content: str) -> Optional[str]:
    """Extract <title> from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        title = re.sub(r"\s+", " ", title)
        return title
    return None
