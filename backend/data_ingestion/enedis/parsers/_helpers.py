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


def parse_xml_root(
    xml_bytes: bytes,
    expected_tag: str,
    error_cls: type[Exception],
) -> ET.Element:
    """Parse XML bytes, validate root tag, return root element.

    Raises error_cls on invalid XML or unexpected root tag.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise error_cls(f"Invalid XML: {exc}") from exc

    root_tag = strip_ns(root.tag)
    if root_tag != expected_tag:
        raise error_cls(f"Expected root <{expected_tag}>, got <{root_tag}>")
    return root


def header_to_dict(header_elem: ET.Element) -> dict:
    """Extract all direct children of a header element into {tag: text}."""
    return {
        strip_ns(child.tag): (child.text or "").strip()
        for child in header_elem
    }
