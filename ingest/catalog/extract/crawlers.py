"""Extract Crawler classes (extends CrawlerBase)."""

from __future__ import annotations

import re
from pathlib import Path

from catalog.extract.base import (
    classes_of,
    iter_java_files,
    parse_file,
    rel_to_repo,
    start_line,
)
from catalog.models import Edge, Node

_URL_RE = re.compile(
    r'(?:sourceUrl|baseUrl|feedUrl|rssUrl|BASE_URL|FEED_URL|URL)\s*=\s*"([^"]+)"'
)


def extract(repo_root: Path, crawler_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    if not crawler_dir.is_dir():
        return nodes, edges

    for java_file in iter_java_files(crawler_dir):
        if java_file.stem == "CrawlerBase":
            continue
        tree = parse_file(java_file)
        if tree is None:
            continue

        for cls in classes_of(tree):
            if not _extends_crawler_base(cls):
                continue
            text = java_file.read_text(encoding="utf-8")
            url_match = _URL_RE.search(text)

            crawler_id = Node.make_id("Crawler", cls.name)
            nodes.append(
                Node(
                    id=crawler_id,
                    label="Crawler",
                    name=cls.name,
                    file_path=rel_to_repo(java_file, repo_root),
                    start_line=start_line(cls),
                    extra={"sourceUrl": url_match.group(1) if url_match else None},
                )
            )

    return nodes, edges


def _extends_crawler_base(cls) -> bool:
    if cls.extends is None:
        return False
    # cls.extends can be ReferenceType — has .name attr
    return getattr(cls.extends, "name", None) == "CrawlerBase"
