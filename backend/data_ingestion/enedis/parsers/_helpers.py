"""PROMEOS — Shared XML helpers for Enedis flux parsers.

Namespace-tolerant utilities used by all flux parsers (R4x, R171, R50, R151).
These handle the ERDF→ENEDIS namespace variations present in real Enedis files.
"""

import xml.etree.ElementTree as ET


def strip_ns(tag: str) -> str:
    """Remove namespace prefix from an XML tag: {ns}Tag -> Tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def find_child(parent: ET.Element, tag_name: str) -> ET.Element | None:
    """Find first direct child matching tag_name, namespace-tolerant."""
    for child in parent:
        if strip_ns(child.tag) == tag_name:
            return child
    return None


def child_text(parent: ET.Element, tag_name: str) -> str | None:
    """Get text content of first child matching tag_name, or None."""
    elem = find_child(parent, tag_name)
    if elem is not None and elem.text:
        return elem.text.strip()
    return None
