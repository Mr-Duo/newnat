import os
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import asdict, dataclass
from tree_sitter import Node

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
@dataclass
class FunctionInfo:
    file: str
    language: str
    name: str            # short name
    qualified_name: str  # e.g. MyClass.method or (*Server).Start
    kind: str            # function | method | arrow_function | ...
    start_line: int      # 1-based, inclusive
    end_line: int
    signature: str
    source: str
    root_node: Node
    id: int = 0
    parent_id: Optional[int] = None   # id of the enclosing (named) function, if nested
    start_col: int = 0                # 0-based, in bytes, within start_line
    end_col: int = 0                  # 0-based, in bytes, exclusive, within end_line
    start_byte: int = 0
    end_byte: int = 0                 # exclusive
    line_prefix: str = ""             # text on start_line BEFORE the function node
    line_suffix: str = ""             # text on end_line AFTER the function node (no "\\n")
    sha256: str = ""                  # sha256 of the raw function bytes
    raw: bytes = b""                  # exact bytes of the function as in the file
    
# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------
def build_metadata(
    path: Path, src: bytes, lang: str, funcs: list[FunctionInfo],
    raw_files: list[Path], out_dir: Path, meta_path: Path,
) -> dict:
    crlf = src.count(b"\r\n")
    lf = src.count(b"\n")
    line_ending = "lf" if crlf == 0 else ("crlf" if crlf == lf else "mixed")
    ends_nl = src.endswith(b"\n")
    try:
        src.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        encoding = "unknown (not valid utf-8)"
    meta_dir = meta_path.resolve().parent

    return {
        "format_version": 1,
        "notes": [
            "Lines are 1-based and inclusive; columns are 0-based BYTE offsets, end exclusive.",
            "Original lines start_line..end_line == line_prefix + <raw function bytes> + line_suffix "
            "(each line ending with the file's line_ending).",
            "Apply edits to the original file from the highest start_byte to the lowest, or "
            "re-run extraction after each change. Nested functions (parent_id != null) overlap "
            "their parent's byte range - do not edit both in the same pass.",
            "Before diffing, check source_file.sha256 and each function's sha256 still match.",
        ],
        "source_file": {
            "path": str(path),
            "absolute_path": str(path.resolve()),
            "language": lang,
            "encoding": encoding,
            "line_ending": line_ending,
            "ends_with_newline": ends_nl,
            "line_count": src.count(b"\n") + (0 if ends_nl or not src else 1),
            "size_bytes": len(src),
            "sha256": hashlib.sha256(src).hexdigest(),
        },
        "raw_dir": os.path.relpath(out_dir, meta_dir).replace(os.sep, "/"),
        "functions": [
            {
                "id": fn.id,
                "parent_id": fn.parent_id,
                "raw_file": rf.name,
                "name": fn.name,
                "qualified_name": fn.qualified_name,
                "kind": fn.kind,
                "signature": fn.signature,
                "location": {
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                    "start_col": fn.start_col,
                    "end_col": fn.end_col,
                    "start_byte": fn.start_byte,
                    "end_byte": fn.end_byte,
                },
                "line_prefix": fn.line_prefix,
                "line_suffix": fn.line_suffix,
                "sha256": fn.sha256,
            }
            for fn, rf in zip(funcs, raw_files)
        ],
    }