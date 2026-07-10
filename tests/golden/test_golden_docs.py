"""
Golden-document tests: each source document under `documents/` is converted by the model
and serialized three ways (`report.yaml`, `docgraph.yaml`, `reassembled.md`); the
serializations are committed under `expected/<doc>/` and compared on every run.

This is transparent-box testing — one readable artifact per document shows every
projection at once, so any change to any view appears in a diff. Alongside the raw diff,
`test_model_invariants` enforces the model's hard guarantees programmatically, so a
semantic violation fails even if the goldens are regenerated without review.

Source documents are Markdown with YAML frontmatter (`name`, `description`, optional
`item_partition_depth`). Regenerate goldens after an intentional change with:

    UPDATE_GOLDEN=1 uv run pytest tests/golden/test_golden_docs.py

then review `git diff tests/golden/expected/`.
"""

from __future__ import annotations

import difflib
import os
from pathlib import Path

from frontmatter_format import fmf_read

from flexdoc.docs import FlexDoc
from flexdoc.docs.block_types import BlockType
from flexdoc.docs.collect import INLINE_KINDS
from flexdoc.docs.debug import doc_graph_yaml, doc_report, doc_report_data
from flexdoc.docs.links import NAVIGABLE_LINK_FORMS, LinkForm
from flexdoc.docs.node import Layer, NodeKind

_HERE = Path(__file__).parent
_DOCS_DIR = _HERE / "documents"
_EXPECTED_DIR = _HERE / "expected"
_UPDATE = bool(os.environ.get("UPDATE_GOLDEN"))


def _docs() -> list[Path]:
    return sorted(_DOCS_DIR.glob("*.md"))


def _load(path: Path) -> tuple[str, int]:
    """Return the document body and its `item_partition_depth` option (default 6)."""
    content, meta = fmf_read(path)
    depth = 6
    if meta and "item_partition_depth" in meta:
        depth = int(meta["item_partition_depth"])  # pyright: ignore[reportArgumentType]
    return content, depth


def _artifacts(content: str, depth: int) -> dict[str, str]:
    td = FlexDoc.from_text(content)
    return {
        "report.yaml": doc_report(td, item_partition_depth=depth),
        "docgraph.yaml": doc_graph_yaml(td),
        "reassembled.md": td.reassemble(),
    }


def test_golden_artifacts():
    docs = _docs()
    assert docs, f"no corpus documents found in {_DOCS_DIR}"

    failures: list[str] = []
    for path in docs:
        content, depth = _load(path)
        artifacts = _artifacts(content, depth)
        dest = _EXPECTED_DIR / path.stem

        if _UPDATE:
            dest.mkdir(parents=True, exist_ok=True)
            for name, text in artifacts.items():
                (dest / name).write_text(text, encoding="utf-8")
            continue

        for name, actual in artifacts.items():
            golden_path = dest / name
            if not golden_path.exists():
                failures.append(f"{path.stem}/{name}: missing golden (run UPDATE_GOLDEN=1)")
                continue
            expected = golden_path.read_text(encoding="utf-8")
            if actual != expected:
                diff = "".join(
                    difflib.unified_diff(
                        expected.splitlines(keepends=True),
                        actual.splitlines(keepends=True),
                        fromfile=f"golden/{name}",
                        tofile=f"actual/{name}",
                    )
                )
                failures.append(f"{path.stem}/{name} differs:\n{diff}")

    if _UPDATE:
        return
    if failures:
        raise AssertionError("\n\n".join(failures))


def test_model_invariants():
    """The model's hard guarantees, checked independently of the golden diff."""
    docs = _docs()
    assert docs, f"no corpus documents found in {_DOCS_DIR}"

    for path in docs:
        content, depth = _load(path)
        td = FlexDoc.from_text(content)
        source = td.source_text or td.reassemble()
        data = doc_report_data(td, item_partition_depth=depth)
        where = path.stem

        # Base-block partition: ordered, pairwise non-overlapping, and covering every
        # non-whitespace character exactly once (P13) — the documented contract, not just
        # "some block touches each char".
        spans = [b.block.span for b in td.base_blocks(item_partition_depth=depth)]
        assert spans == sorted(spans), f"{where}: base blocks not in source order"
        for i in range(len(spans) - 1):
            assert spans[i][1] <= spans[i + 1][0], f"{where}: base-block spans overlap at {i}"
        cover: dict[int, int] = {}
        for s, e in spans:
            for i in range(s, e):
                cover[i] = cover.get(i, 0) + 1
        content_offset = td._content_offset()
        for i, ch in enumerate(source[content_offset:], start=content_offset):
            if not ch.isspace():
                assert cover.get(i, 0) == 1, (
                    f"{where}: char {i} ({ch!r}) covered {cover.get(i, 0)}x"
                )

        # Every located inline node round-trips through SpanRef (P6/SpanRef).
        for row in data["spanrefs"]:
            assert row["ok"], f"{where}: SpanRef did not round-trip for {row['id']}"

        table = td.node_table()
        # Node ids unique and every parent/child reference resolves.
        assert len(table.nodes) == len({n.id for n in table.nodes.values()})
        for nid, n in table.nodes.items():
            if n.parent is not None:
                assert n.parent in table.nodes, f"{where}: dangling parent {n.parent} on {nid}"
            for cid in n.children:
                assert cid in table.nodes, f"{where}: dangling child {cid} on {nid}"
            # Source-backed block/section nodes are span-exact and whitespace-trimmed (P6).
            if n.source_span is not None:
                s, e = n.source_span
                assert 0 <= s <= e <= len(source)

        # DocGraph child references are all valid within the projection.
        ids = {nm.id for nm in td.graph().nodes}
        for nm in td.graph().nodes:
            for cid in nm.children:
                assert cid in ids, f"{where}: docgraph child {cid} missing for {nm.id}"

        # Cross-projection: sections()/toc() recover exactly the top-level heading blocks,
        # with matching titles in document order (the contract Bug 2 broke).
        heading_blocks = [b for b in td.blocks() if b.type == BlockType.heading]
        toc = td.toc()
        assert len(toc) == len(heading_blocks), (
            f"{where}: toc has {len(toc)} entries, {len(heading_blocks)} top-level headings"
        )
        assert [title for _level, title, _span in toc] == [
            b.heading_info.title if b.heading_info else "" for b in heading_blocks
        ], f"{where}: toc titles do not match heading-block titles"

        # Every located markdown inline node lies within its parent block's span — the
        # nesting guarantee asserted on the query surface (the contract Bug 1 broke).
        for n in table.nodes.values():
            if n.layer is not Layer.markdown or n.kind not in INLINE_KINDS:
                continue
            if n.parent is None or n.source_span is None:
                continue
            p_span = table.nodes[n.parent].source_span
            assert (
                p_span is not None
                and p_span[0] <= n.source_span[0] <= n.source_span[1] <= p_span[1]
            ), f"{where}: inline {n.id} span {n.source_span} escapes parent {p_span}"

        # Reference-definition nodes are block-attached, never deliberate roots: each
        # link_ref_def with a span has a containing parent and is found scoped to it (the
        # contract the escaped, untrimmed ref-def span broke).
        for n in table.nodes.values():
            if n.kind is not NodeKind.link_ref_def or n.source_span is None:
                continue
            assert n.parent is not None, f"{where}: link_ref_def {n.id} unparented"
            p_span = table.nodes[n.parent].source_span
            assert (
                p_span is not None
                and p_span[0] <= n.source_span[0] <= n.source_span[1] <= p_span[1]
            ), f"{where}: link_ref_def {n.id} span {n.source_span} escapes parent {p_span}"
            assert any(
                c.id == n.id for c in td.collect(within=n.parent, kinds={NodeKind.link_ref_def})
            ), f"{where}: link_ref_def {n.id} not found scoped to its block"

        # The public inline query path builds without raising for every inline kind (Bug 1
        # broke this through collect()/graph(), not only the internal build).
        for kind in INLINE_KINDS:
            td.collect(kinds={kind})  # inline kinds need no recursive=True
            td.collect(kinds={kind}, recursive=True)

        # Link-form accounting: every links() entry is a true link, and the per-form lists
        # match the node-table node counts one-for-one.
        assert all(link.link_form in NAVIGABLE_LINK_FORMS for link in td.links())
        assert len(td.links()) == len(table.by_kind(NodeKind.link)), f"{where}: link count"
        assert len(td.images()) == len(table.by_kind(NodeKind.image)), f"{where}: image count"
        assert len(td.links(link_forms={LinkForm.reference_definition})) == len(
            table.by_kind(NodeKind.link_ref_def)
        ), f"{where}: reference-definition count"

        # Normalized-form idempotence (P11): `reassemble()` produces the editing view's
        # normalized text (which may differ from the source for constructs the editing
        # view normalizes, e.g. multi-line reference definitions). Re-parsing and
        # re-reassembling that normalized text must be a fixed point.
        normalized = td.reassemble()
        renormalized = FlexDoc.from_text(normalized).reassemble()
        assert normalized == renormalized, f"{where}: reassemble() is not idempotent"


_REPO_ROOT = _HERE.parent.parent


def _repo_markdown() -> list[Path]:
    """Every Markdown file under the repo, minus generated golden artifacts and vendored
    trees. Real documents combine constructs the curated corpus does not, so parsing them
    is a cheap, self-renewing fuzz over the model (it reproduces the pprose discovery that
    found these bugs); this repo's own `AGENTS.md` alone exercises marker-preceded headings."""
    skip = {".venv", "node_modules", ".git", "expected"}
    return sorted(
        p for p in _REPO_ROOT.rglob("*.md") if not (set(p.relative_to(_REPO_ROOT).parts) & skip)
    )


def test_repo_markdown_invariants():
    """Parsing the repo's own Markdown must never crash and must hold the cross-projection
    contracts (toc parity, inline nesting, the public inline query path). No goldens — only
    invariants — so the suite self-renews as the repo's docs evolve."""
    docs = _repo_markdown()
    assert docs, f"no Markdown found under {_REPO_ROOT}"

    for path in docs:
        where = str(path.relative_to(_REPO_ROOT))
        td = FlexDoc.from_text(path.read_text(encoding="utf-8"))
        table = td.node_table()  # the build that Bug 1 crashed on real input

        heading_blocks = [b for b in td.blocks() if b.type == BlockType.heading]
        assert len(td.toc()) == len(heading_blocks), f"{where}: toc/heading-block mismatch"

        for n in table.nodes.values():
            if n.layer is not Layer.markdown or n.kind not in INLINE_KINDS:
                continue
            if n.parent is None or n.source_span is None:
                continue
            p_span = table.nodes[n.parent].source_span
            assert (
                p_span is not None
                and p_span[0] <= n.source_span[0] <= n.source_span[1] <= p_span[1]
            ), f"{where}: inline {n.id} escapes its parent block"

        for kind in INLINE_KINDS:
            td.collect(kinds={kind}, recursive=True)
        td.graph()
        td.prose_text()
