#!/usr/bin/env python3
"""
Parse ONE source file with tree-sitter and:
  1. write the raw source of every function/method into its own file in a folder
     (default: ./raw), and
  2. write meta-data.json describing where each function came from (file, lines,
     columns, byte offsets, hashes), so edited functions can later be turned into
     a unified diff and applied with `git apply`.

Install:
    pip install tree-sitter tree-sitter-python tree-sitter-go tree-sitter-javascript
    # optional: pip install tree-sitter-typescript

Usage:
    python extract_functions.py path/to/file.py                # raw/ + meta-data.json
    python extract_functions.py main.go -o out_dir             # out_dir/ + meta-data.json next to it
    python extract_functions.py app.js --meta /tmp/meta.json
    python extract_functions.py app.js --include-anonymous
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

from pathlib import Path
from typing import Iterator, Optional
from collections import defaultdict

from tree_sitter import Language, Node, Parser, Tree

from newnat.utils import *
from newnat.data_models import *

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def function_name(node: Node, lang: str, src: bytes) -> str:
    """Best-effort name for a function node ('' if anonymous)."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return text_of(name_node, src)

    # JS/TS: `const foo = () => {}`, `obj.foo = function() {}`, `{ foo: () => {} }`,
    # class fields `foo = () => {}`
    if lang in ("javascript", "typescript", "tsx"):
        p = node.parent
        if p is None:
            return ""
        if p.type == "variable_declarator":
            return text_of(p.child_by_field_name("name"), src)
        if p.type == "assignment_expression":
            return text_of(p.child_by_field_name("left"), src)
        if p.type == "pair":
            return text_of(p.child_by_field_name("key"), src).strip("'\"")
        if p.type in ("field_definition", "public_field_definition"):
            return text_of(p.child_by_field_name("property")
                           or p.child_by_field_name("name"), src)
    return ""


def go_receiver_type(node: Node, src: bytes) -> str:
    recv = node.child_by_field_name("receiver")
    if recv is None:
        return ""
    t = first_descendant(recv, {"type_identifier"})
    name = text_of(t, src)
    is_ptr = first_descendant(recv, {"pointer_type"}) is not None
    return f"(*{name})" if is_ptr else name


def signature_of(node: Node, src: bytes) -> str:
    """Source text from start of the function up to the start of its body."""
    body = node.child_by_field_name("body")
    end = body.start_byte if body is not None else node.end_byte
    sig = src[node.start_byte:end].decode("utf-8", errors="replace")
    return " ".join(sig.split()).rstrip("{:").rstrip()

# --------------------------------------------------------------------------
# Core extraction
# --------------------------------------------------------------------------
def extract_functions(
    src: bytes,
    lang: str,
    tree = Tree,
    file: str = "<memory>",
    include_anonymous: bool = False,
) -> list[FunctionInfo]:
    cfg = LANGUAGE_CONFIG[lang]
    results: list[FunctionInfo] = []

    next_id = 0

    def visit(
        node: Node, 
        scope: tuple[tuple[str, str, Optional[int]], ...]
    ) -> Iterator[FunctionInfo]:
        nonlocal next_id
        new_scope = scope

        if node.type in cfg["functions"]:
            name = function_name(node, lang, src)
            fn_id: Optional[int] = None
            if name or include_anonymous:
                fn_id = next_id
                next_id += 1
                display = name or "<anonymous>"
                enclosing_kind = scope[-1][0] if scope else ""

                # Decide kind + qualified name
                kind = "function"
                qual_prefix = ".".join(n for _, n, _ in scope)
                if lang == "go" and node.type == "method_declaration":
                    kind = "method"
                    qual_prefix = go_receiver_type(node, src)
                elif node.type == "method_definition" or enclosing_kind == "class":
                    kind = "method"
                elif node.type == "arrow_function":
                    kind = "arrow_function"

                qualified = f"{qual_prefix}.{display}" if qual_prefix else display
                parent_id = next(
                    (i for k, _, i in reversed(scope) if k == "function" and i is not None), None
                )
                sb, eb = node.start_byte, node.end_byte
                line_start = src.rfind(b"\n", 0, sb) + 1
                nl = src.find(b"\n", eb)
                line_end = len(src) if nl == -1 else nl
                raw = src[sb:eb]
                yield FunctionInfo(
                    file=file,
                    language=lang,
                    name=display,
                    qualified_name=qualified,
                    kind=kind,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=signature_of(node, src),
                    source=text_of(node, src),
                    id=fn_id,
                    parent_id=parent_id,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    start_byte=sb,
                    end_byte=eb,
                    line_prefix=src[line_start:sb].decode("utf-8", errors="replace"),
                    line_suffix=src[eb:line_end].decode("utf-8", errors="replace"),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    raw=raw,
                    root_node=node,
                )
            new_scope = scope + (("function", name or "<anonymous>", fn_id),)

        elif node.type in cfg["classes"]:
            cname = text_of(node.child_by_field_name("name"), src) or "<anonymous class>"
            new_scope = scope + (("class", cname, None),)

        for child in node.children:
            yield from visit(child, new_scope)

    results.extend(visit(tree.root_node, ()))
    return results


def extract_from_file(path: Path, **kwargs) -> tuple[bytes, str, list[FunctionInfo]]:
    """Returns (file_bytes, language, functions)."""
    tree = get_tree(path)
    lang = EXT_TO_LANG.get(path.suffix.lower())
    if lang is None:
        return b"", "", []
    src = path.read_bytes()
    return src, lang, extract_functions(src, lang, file=str(path), tree=tree, **kwargs)

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(path: Path, out_dir='.', meta_path="meta-data.json") \
    -> tuple[list[FunctionInfo], bytes]:

    try:
        src, lang, funcs = extract_from_file(
            path, 
            include_anonymous=False
        )
    except ImportError as e:
        sys.exit(f"error: grammar not installed ({e})")

    written = write_raw_functions(funcs, out_dir, path.suffix)
    meta = build_metadata(path, src, lang, funcs, written, out_dir, meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for fn, out in zip(funcs, written):
        print(f"{out}  <-  [{fn.kind}] {fn.qualified_name} (lines {fn.start_line}-{fn.end_line})")
    print(f"\n{len(written)} function(s) written to {out_dir}/", file=sys.stderr)
    print(f"metadata written to {meta_path}", file=sys.stderr)

    return funcs, lang, src

if __name__ == "__main__":
    main()