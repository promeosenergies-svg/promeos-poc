"""
PROMEOS KB - HTML Ingestion Pipeline
Sanitize → Structure → Chunk → Generate YAML drafts

PIPELINE:
1. Ingest raw HTML (file/folder/zip)
2. Sanitize (remove nav/footer/scripts, extract main content)
3. Structure (extract H1/H2/H3, anchors, tables, lists)
4. Chunk (1 chunk = 1 section, 200-800 words)
5. Generate YAML drafts (rules/knowledge/checklists)
6. Track in manifest/backlog
7. Optional: auto-import + reindex
"""

import os
import re
import hashlib
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from html.parser import HTMLParser
import zipfile
import shutil


class HTMLSanitizer(HTMLParser):
    """
    Strip unwanted tags, extract main content
    """

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_section = None
        self.skip_tags = {"script", "style", "nav", "footer", "aside", "header"}
        self.in_skip = False

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.in_skip = True
        elif tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            self.text_parts.append(f"\n\n{'#' * int(tag[1])} ")
        elif tag == "p":
            self.text_parts.append("\n\n")
        elif tag == "br":
            self.text_parts.append("\n")
        elif tag == "li":
            self.text_parts.append("\n- ")

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False

    def handle_data(self, data):
        if not self.in_skip:
            text = data.strip()
            if text:
                self.text_parts.append(text + " ")

    def get_text(self):
        return "".join(self.text_parts).strip()


class HTMLIngestionPipeline:
    """
    Complete HTML ingestion pipeline
    """

    def __init__(self, sources_dir: str = "docs/sources/html"):
        self.sources_dir = Path(sources_dir)
        self.sources_dir.mkdir(parents=True, exist_ok=True)

    def ingest(
        self,
        input_path: str,
        doc_id: str,
        title: Optional[str] = None,
        updated_at: Optional[str] = None,
        auto_import: bool = False,
    ) -> Dict[str, Any]:
        """
        Main ingestion pipeline

        Args:
            input_path: Path to HTML file/folder/zip
            doc_id: Unique document ID
            title: Document title (auto-detect if None)
            updated_at: ISO date (use today if None)
            auto_import: Import generated drafts to DB

        Returns:
            Report dict with stats and paths
        """
        print(f"[HTML Ingest] Starting pipeline for doc_id={doc_id}")

        # 1. Ingest raw
        raw_dir = self.sources_dir / doc_id / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        html_content = self._ingest_raw(input_path, raw_dir)
        if not html_content:
            return {"error": "Failed to read HTML content"}

        # Compute content hash
        content_hash = hashlib.sha256(html_content.encode()).hexdigest()[:16]

        # 2. Sanitize
        print(f"[HTML Ingest] Sanitizing HTML...")
        clean_text = self._sanitize_html(html_content)

        # Auto-detect title if not provided
        if not title:
            title = self._extract_title(html_content, doc_id)

        # 3. Structure
        print(f"[HTML Ingest] Structuring content...")
        sections = self._structure_content(clean_text)

        # 4. Chunk
        print(f"[HTML Ingest] Chunking sections...")
        chunks = self._chunk_sections(sections, doc_id)

        # Save clean.md
        clean_dir = self.sources_dir / doc_id / "clean"
        clean_dir.mkdir(parents=True, exist_ok=True)
        clean_md_path = clean_dir / "clean.md"
        with open(clean_md_path, "w", encoding="utf-8") as f:
            f.write(clean_text)

        # Save chunks.json
        chunks_dir = self.sources_dir / doc_id / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        chunks_json_path = chunks_dir / "chunks.json"
        with open(chunks_json_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        # 5. Generate YAML drafts
        print(f"[HTML Ingest] Generating YAML drafts...")
        drafts = self._generate_drafts(chunks, doc_id, title)

        # Save drafts
        drafts_dir = Path("docs/kb/drafts") / doc_id
        drafts_dir.mkdir(parents=True, exist_ok=True)

        for draft in drafts:
            draft_path = drafts_dir / f"{draft['id']}.yaml"
            with open(draft_path, "w", encoding="utf-8") as f:
                yaml.dump(draft, f, allow_unicode=True, sort_keys=False)

        # 6. Save meta.json
        meta = {
            "doc_id": doc_id,
            "title": title,
            "content_hash": content_hash,
            "nb_sections": len(sections),
            "nb_chunks": len(chunks),
            "nb_drafts": len(drafts),
            "updated_at": updated_at or datetime.now().isoformat()[:10],
            "ingested_at": datetime.now().isoformat(),
        }

        meta_path = self.sources_dir / doc_id / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # 7. Auto-import (if requested)
        if auto_import:
            print(f"[HTML Ingest] Auto-importing drafts...")
            # This would call kb_seed_import.py or store.upsert_item()
            # For now, just log
            print(f"[HTML Ingest] Auto-import not yet implemented")

        # Report
        report = {
            "doc_id": doc_id,
            "title": title,
            "content_hash": content_hash,
            "nb_sections": len(sections),
            "nb_chunks": len(chunks),
            "nb_drafts": len(drafts),
            "paths": {
                "raw": str(raw_dir),
                "clean_md": str(clean_md_path),
                "chunks_json": str(chunks_json_path),
                "drafts": str(drafts_dir),
                "meta": str(meta_path),
            },
        }

        # 8. Generate ingest_report.md
        report_md = self._generate_ingest_report(report, drafts, sections)
        report_md_path = self.sources_dir / doc_id / "ingest_report.md"
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        report["paths"]["ingest_report"] = str(report_md_path)

        print(f"[HTML Ingest] Pipeline complete!")
        print(f"  - {len(sections)} sections")
        print(f"  - {len(chunks)} chunks")
        print(f"  - {len(drafts)} YAML drafts")
        print(f"  - Report: {report_md_path}")

        return report

    def _ingest_raw(self, input_path: str, raw_dir: Path) -> Optional[str]:
        """Ingest raw HTML from file/folder/zip"""
        input_path = Path(input_path)

        if input_path.is_file():
            if input_path.suffix == ".html":
                # Copy HTML file
                shutil.copy(input_path, raw_dir / input_path.name)
                with open(input_path, "r", encoding="utf-8") as f:
                    return f.read()
            elif input_path.suffix == ".zip":
                # Extract zip
                with zipfile.ZipFile(input_path, "r") as zip_ref:
                    zip_ref.extractall(raw_dir)
                # Find first HTML file
                html_files = list(raw_dir.glob("**/*.html"))
                if html_files:
                    with open(html_files[0], "r", encoding="utf-8") as f:
                        return f.read()
        elif input_path.is_dir():
            # Copy directory
            shutil.copytree(input_path, raw_dir, dirs_exist_ok=True)
            # Find first HTML file
            html_files = list(raw_dir.glob("**/*.html"))
            if html_files:
                with open(html_files[0], "r", encoding="utf-8") as f:
                    return f.read()

        return None

    def _sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML and convert to clean markdown-ish text"""
        parser = HTMLSanitizer()
        parser.feed(html_content)
        text = parser.get_text()

        # Clean whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        return text.strip()

    def _extract_title(self, html_content: str, fallback: str) -> str:
        """Extract title from HTML <title> or <h1>"""
        # Try <title>
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()

        # Try <h1>
        h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html_content, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()

        return fallback

    def _structure_content(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract sections based on headers
        Returns: [{level: 1, title: "...", content: "...", anchor: "#..."}]
        """
        sections = []
        lines = text.split("\n")

        current_section = None

        for line in lines:
            # Check if line is a header
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if header_match:
                # Save previous section
                if current_section and current_section.get("content"):
                    sections.append(current_section)

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                anchor = self._generate_anchor(title)

                current_section = {"level": level, "title": title, "anchor": anchor, "content": ""}
            else:
                # Append to current section
                if current_section:
                    current_section["content"] += line + "\n"

        # Save last section
        if current_section and current_section.get("content"):
            sections.append(current_section)

        return sections

    def _generate_anchor(self, title: str) -> str:
        """Generate URL anchor from title"""
        anchor = title.lower()
        anchor = re.sub(r"[^a-z0-9\s-]", "", anchor)
        anchor = re.sub(r"\s+", "-", anchor)
        return f"#{anchor}"

    def _chunk_sections(self, sections: List[Dict], doc_id: str) -> List[Dict[str, Any]]:
        """
        Chunk sections (target 200-800 words, split >1200, merge <100)
        """
        chunks = []
        chunk_index = 0

        for section in sections:
            content = section["content"].strip()
            if not content:
                continue

            word_count = len(content.split())

            # If too long, split by paragraphs
            if word_count > 1200:
                paragraphs = content.split("\n\n")
                buffer = ""
                buffer_words = 0

                for para in paragraphs:
                    para_words = len(para.split())
                    if buffer_words + para_words > 800:
                        # Flush buffer as chunk
                        if buffer:
                            chunks.append(
                                {
                                    "chunk_id": f"{doc_id}_chunk_{chunk_index}",
                                    "doc_id": doc_id,
                                    "section_path": section["title"],
                                    "anchor": section["anchor"],
                                    "text": buffer.strip(),
                                    "word_count": buffer_words,
                                    "chunk_index": chunk_index,
                                }
                            )
                            chunk_index += 1
                        buffer = para
                        buffer_words = para_words
                    else:
                        buffer += "\n\n" + para
                        buffer_words += para_words

                # Flush remaining
                if buffer:
                    chunks.append(
                        {
                            "chunk_id": f"{doc_id}_chunk_{chunk_index}",
                            "doc_id": doc_id,
                            "section_path": section["title"],
                            "anchor": section["anchor"],
                            "text": buffer.strip(),
                            "word_count": buffer_words,
                            "chunk_index": chunk_index,
                        }
                    )
                    chunk_index += 1

            else:
                # Single chunk
                chunks.append(
                    {
                        "chunk_id": f"{doc_id}_chunk_{chunk_index}",
                        "doc_id": doc_id,
                        "section_path": section["title"],
                        "anchor": section["anchor"],
                        "text": content,
                        "word_count": word_count,
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1

        return chunks

    def _generate_drafts(self, chunks: List[Dict], doc_id: str, doc_title: str) -> List[Dict[str, Any]]:
        """
        Generate YAML draft KB items from chunks
        Heuristics:
        - obligation/seuil/deadline/sanction → type: rule
        - ratios/usages/heuristiques → type: knowledge
        - étapes/procédure/pièces → type: checklist
        """
        drafts = []

        for chunk in chunks:
            text = chunk["text"].lower()
            section_title = chunk["section_path"]

            # Detect type (heuristic)
            if any(kw in text for kw in ["obligation", "seuil", "deadline", "sanction", "décret", "loi", "article"]):
                draft_type = "rule"
            elif any(kw in text for kw in ["ratio", "usage", "heuristique", "moyenne", "typique"]):
                draft_type = "knowledge"
            elif any(kw in text for kw in ["étapes", "procédure", "pièces", "checklist", "liste"]):
                draft_type = "checklist"
            else:
                draft_type = "knowledge"  # Default

            # Generate ID
            draft_id = f"{doc_id}_{chunk['chunk_index']}"

            # Detect domain (heuristic)
            domain = "reglementaire"  # Default
            if any(kw in text for kw in ["consommation", "usage", "profil"]):
                domain = "usages"
            elif any(kw in text for kw in ["autoconsommation", "acc", "collective"]):
                domain = "acc"
            elif any(kw in text for kw in ["facture", "tarif", "prix"]):
                domain = "facturation"

            # Create draft
            draft = {
                "id": draft_id,
                "type": draft_type,
                "domain": domain,
                "title": section_title or f"Section {chunk['chunk_index']}",
                "summary": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "tags": {"energy": ["multi"], "segment": [], "asset": [], "reg": [], "granularity": []},
                "scope": None,
                "content_md": chunk["text"],
                "logic": None,
                "sources": [
                    {
                        "doc_id": doc_id,
                        "label": doc_title,
                        "section": chunk["section_path"],
                        "anchor": chunk["anchor"],
                        "excerpt_short": chunk["text"][:100] + "...",
                    }
                ],
                "updated_at": datetime.now().isoformat()[:10],
                "confidence": "low",  # Auto-generated = low confidence
                "status": "draft",  # LIFECYCLE: auto-generated items are always drafts
                "priority": 3,
                "notes": "Auto-generated draft from HTML ingestion. Requires human review and upgrade.",
            }

            drafts.append(draft)

        return drafts

    def _generate_ingest_report(self, report: Dict[str, Any], drafts: List[Dict], sections: List[Dict]) -> str:
        """Generate a markdown ingestion report"""
        lines = []
        lines.append(f"# Ingestion Report: {report['doc_id']}")
        lines.append(f"")
        lines.append(f"**Title:** {report['title']}")
        lines.append(f"**Content Hash:** {report['content_hash']}")
        lines.append(f"**Ingested at:** {datetime.now().isoformat()[:19]}")
        lines.append(f"")
        lines.append(f"## Pipeline Summary")
        lines.append(f"")
        lines.append(f"| Step | Count |")
        lines.append(f"|------|-------|")
        lines.append(f"| Sections extracted | {report['nb_sections']} |")
        lines.append(f"| Chunks generated | {report['nb_chunks']} |")
        lines.append(f"| YAML drafts created | {report['nb_drafts']} |")
        lines.append(f"")

        # Draft type breakdown
        type_counts = {}
        domain_counts = {}
        for d in drafts:
            type_counts[d.get("type", "?")] = type_counts.get(d.get("type", "?"), 0) + 1
            domain_counts[d.get("domain", "?")] = domain_counts.get(d.get("domain", "?"), 0) + 1

        lines.append(f"## Drafts by Type")
        lines.append(f"")
        for t, c in sorted(type_counts.items()):
            lines.append(f"- **{t}**: {c}")
        lines.append(f"")

        lines.append(f"## Drafts by Domain")
        lines.append(f"")
        for d, c in sorted(domain_counts.items()):
            lines.append(f"- **{d}**: {c}")
        lines.append(f"")

        # Sections detail
        lines.append(f"## Sections")
        lines.append(f"")
        for i, s in enumerate(sections):
            lines.append(f"{i + 1}. **{s['title']}** (level {s['level']}, {len(s['content'].split())} words)")
        lines.append(f"")

        # Drafts detail
        lines.append(f"## Generated Drafts")
        lines.append(f"")
        lines.append(f"| ID | Type | Domain | Confidence | Status |")
        lines.append(f"|----|------|--------|------------|--------|")
        for d in drafts:
            lines.append(
                f"| {d['id']} | {d['type']} | {d['domain']} | {d['confidence']} | {d.get('status', 'draft')} |"
            )
        lines.append(f"")

        # Next steps
        lines.append(f"## Next Steps")
        lines.append(f"")
        lines.append(f"1. Review drafts in `docs/kb/drafts/{report['doc_id']}/`")
        lines.append(f"2. Upgrade confidence and refine tags/logic for each draft")
        lines.append(f"3. Promote to validated: `python backend/scripts/kb_promote_item.py <file.yaml>`")
        lines.append(f"4. Import to DB: `python backend/scripts/kb_seed_import.py --include-drafts`")
        lines.append(f"5. Rebuild FTS index: `python backend/scripts/kb_build_index.py`")
        lines.append(f"")

        return "\n".join(lines)
