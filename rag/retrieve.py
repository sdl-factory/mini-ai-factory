"""Retrieval with document-level access control.

Every document declares the groups allowed to read it; every chunk inherits that list.
At query time the user's groups come from the directory (the identity provider), never
from the request, and chunks the user can't read are removed BEFORE ranking. Ranking is
simple word overlap: retrieval quality is not the point here, permissions are.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

RAG_DIR = Path(__file__).parent
DOCS_DIR = RAG_DIR / "docs"
DIRECTORY_PATH = RAG_DIR / "directory.json"

WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    {"a", "an", "and", "are", "at", "be", "by", "for", "from", "in", "is", "it", "no"}
    | {"of", "on", "or", "the", "this", "to", "was", "with"}
)


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    position: int
    text: str
    allowed_groups: frozenset[str]


def parse_document(doc_id: str, raw: str) -> list[Chunk]:
    """Split a document into paragraphs; every chunk carries the document's ACL."""
    header, _, body = raw.partition("\n\n")
    fields = dict(line.split(":", 1) for line in header.splitlines() if ":" in line)
    title = fields.get("title", doc_id).strip()
    groups = frozenset(g.strip() for g in fields.get("allowed_groups", "").split(",") if g.strip())
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    return [Chunk(doc_id, title, i, text, groups) for i, text in enumerate(paragraphs)]


def load_index(docs_dir: Path = DOCS_DIR) -> list[Chunk]:
    index: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        index += parse_document(path.stem, path.read_text(encoding="utf-8"))
    return index


def load_directory(path: Path = DIRECTORY_PATH) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def groups_for(user: str, directory: dict[str, list[str]]) -> frozenset[str]:
    """Unknown users belong to no group, so they can read nothing."""
    return frozenset(directory.get(user, []))


def can_read(groups: frozenset[str], chunk: Chunk) -> bool:
    """Deny by default: a chunk without allowed groups is readable by nobody."""
    return bool(chunk.allowed_groups & groups)


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower())) - STOPWORDS


def score(query: str, chunk: Chunk) -> int:
    return len(words(query) & words(f"{chunk.title} {chunk.text}"))


def retrieve(
    query: str, user: str, *, index: list[Chunk], directory: dict[str, list[str]], k: int = 3
) -> list[Chunk]:
    """Return the k best chunks the user may read: filter first, then rank."""
    groups = groups_for(user, directory)
    permitted = [chunk for chunk in index if can_read(groups, chunk)]
    scored = [(score(query, chunk), chunk) for chunk in permitted]
    ranked = sorted(
        (item for item in scored if item[0] > 0),
        key=lambda item: (-item[0], item[1].doc_id, item[1].position),
    )
    return [chunk for _, chunk in ranked[:k]]
