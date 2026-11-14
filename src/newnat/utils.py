import re
import sys
import json
import importlib
import random
import numpy as np

from pathlib import Path
from tree_sitter import Language, Node, Parser, Tree
from collections import deque
from typing import Optional, List, Iterable
from newnat.data_models import FunctionInfo

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

# Directiories
ROOT_DIR = Path(__file__).parent.parent.parent
SRC_DIR = Path(__file__).parent
CONFIG_DIR = SRC_DIR / "config"
OUTPUT_DIR = ROOT_DIR / "output"

# Languages
LANGUAGE_CONFIG_FILE = CONFIG_DIR / "languages.json"
LANGUAGE_CONFIG = dict(json.load(open(LANGUAGE_CONFIG_FILE)))
LANGUAGE_SUPPORT = str(LANGUAGE_CONFIG.keys())
EXT_TO_LANG = {ext: name for name, cfg in LANGUAGE_CONFIG.items() for ext in cfg["exts"]}

# System
sys.setrecursionlimit(10_000)
seed = 42
random.seed(seed)
np.random.seed(seed)

# --------------------------------------------------------------------------
# Tree Helpers
# --------------------------------------------------------------------------

_parsers: dict[str, Parser] = {}
def get_parser(lang_name: str) -> Parser:
    if lang_name not in _parsers:
        cfg = LANGUAGE_CONFIG[lang_name]
        mod = importlib.import_module(cfg["module"])
        language = Language(getattr(mod, cfg["factory"])())
        parser = Parser()
        parser.language = language
        _parsers[lang_name] = parser
    return _parsers[lang_name]

_trees: dict[Tree] = {}
def get_tree(file_path: Path) -> Tree:
    if not file_path.is_file():
        sys.exit(f"error: {file_path} is not a file")
    if file_path.suffix.lower() not in EXT_TO_LANG:
        sys.exit(f"error: unsupported extension '{file_path.suffix}' "
                 f"(supported: {', '.join(sorted(EXT_TO_LANG))})")
    if file_path in _trees:
        return _trees[file_path]
    else:    
        lang = EXT_TO_LANG.get(file_path.suffix.lower())
        if lang is None:
            return b"", "", []
        src = file_path.read_bytes()
        tree = get_parser(lang).parse(src)
        _trees[file_path] = tree
        return _trees[file_path]
    
def text_of(node: Optional[Node], src: bytes) -> str:
    if node is None:
        return ""
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

def first_descendant(node: Node, types: set[str]) -> Optional[Node]:
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in types:
            return n
        stack.extend(reversed(n.children))
    return None

def count_children(node: Node) -> int:
    return node.descendant_count - 1

def extract_statement_within_size(
    fn: FunctionInfo, 
    src: bytes,
    min_node: int=1,
    max_node: int=10, 
    endswith: Optional[List[str]]=None, 
) -> list[Node]:
    if endswith is None:
        endswith = ["statement"]
    statements = []

    for current_node in tree_walk(fn.root_node):
        node_count = count_children(current_node)
        current_code = text_of(current_node, src)

        if (
            any(current_node.type.endswith(e) for e in endswith)
            and min_node < node_count < max_node
            and len(current_code) > 0
        ):
            statements.append(current_node)
                
    return statements

def tree_walk(root_node: Node) -> Iterable[Node]:
    queue = deque([root_node])

    while queue:
        current_node = queue.popleft()
        yield current_node
        queue.extend(current_node.children)
        
# --------------------------------------------------------------------------
# Utils
# --------------------------------------------------------------------------

def safe_filename(qualified_name: str) -> str:
    """Turn e.g. '(*Server).Start' or 'Foo.<anonymous>' into a filesystem-safe string."""
    out = re.sub(r"[^A-Za-z0-9_.-]+", "_", qualified_name).strip("_.")
    return out or "anonymous"


def write_raw_functions(Fn: list[FunctionInfo], out_dir: Path, ext: str) -> list[Path]:
    """Write each function's exact bytes to out_dir/<name>__L<start>-<end><ext>."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fn in Fn:
        name = f"{safe_filename(fn.qualified_name)}__L{fn.start_line}-{fn.end_line}{ext}"
        path = out_dir / name
        path.write_bytes(fn.raw)  # byte-exact: preserves CRLF, odd encodings, etc.
        written.append(path)
    return written

def insert_bytes(target: bytes, src: bytes, start_pos: int) -> bytes:
    """Insert `src` into `target` at `start_pos`."""
    _check_range(target, start_pos)
    return target[:start_pos] + src + target[start_pos:]


def remove_bytes(target: bytes, start_pos: int, end_pos: int) -> bytes:
    """Delete target[start_pos:end_pos] (end_pos exclusive)."""
    _check_range(target, start_pos, end_pos)
    return target[:start_pos] + target[end_pos:]


def replace_bytes(target: bytes, src: bytes, start_pos: int, end_pos: int) -> bytes:
    """Delete target[start_pos:end_pos], then insert `src` at `start_pos`."""
    _check_range(target, start_pos, end_pos)
    return target[:start_pos] + src + target[end_pos:]


def _check_range(target: bytes, start: int, end: int | None = None) -> None:
    end = start if end is None else end
    if not (0 <= start <= end <= len(target)):
        raise ValueError(
            f"Invalid range [{start}, {end}) for target of length {len(target)}"
        )

def last_line_indent(node: Node, source: bytes) -> str:
    row, col = node.end_point
    if col == 0 and row > node.start_point[0]:
        row -= 1

    line = source.split(b"\n")[row]
    indent = line[: len(line) - len(line.lstrip(b" \t"))]
    return indent.decode()

def first_line_indent(node: Node, source: bytes) -> str:
    row = node.start_point[0]
    line = source.split(b"\n")[row]
    indent = line[: len(line) - len(line.lstrip(b" \t"))]
    return indent.decode()