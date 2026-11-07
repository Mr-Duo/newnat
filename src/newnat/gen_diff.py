#!/usr/bin/env python3
"""
Build a unified diff (for `git apply`) from:

  * meta-data.json   - written by extract_functions.py (locations, hashes, paths)
  * raw/             - the original functions (as extracted)
  * transform/       - the transformed functions (same file names as in raw/)

Every function whose file in transform/ differs from the original is spliced back
into the original source file at its recorded byte range; the result is diffed
against the original file.

Usage:
    python make_diff.py meta-data.json --transform transform -o changes.patch
    python make_diff.py meta-data.json --raw raw --transform transform --check
    git apply changes.patch                       # run from the repo root

Behaviour worth knowing:
  * A function with no file in transform/ is treated as "unchanged".
  * Trailing/leading blank lines in transformed files are ignored, and line
    endings are converted to the original function's style (LF / CRLF).
  * If a transformed method lost its class indentation (e.g. it was dedented),
    the continuation lines are re-indented to match the original (--reindent).
  * If a function and a function nested inside it are both changed, the outer
    (parent) function wins and the nested edit is dropped with a warning.
  * Refuses to run if the source file changed since extraction (sha256 in the
    metadata) unless --force is given.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterator, Optional

WS = b" \t"


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def split_lines(b: bytes) -> list[bytes]:
    """Split on b'\\n' only, keeping the terminator (a lone \\r is not a line break)."""
    parts = b.split(b"\n")
    lines = [p + b"\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def leading_ws_len(line: bytes) -> int:
    return len(line) - len(line.lstrip(WS))


def min_indent(lines: list[bytes]) -> Optional[int]:
    vals = [leading_ws_len(l) for l in lines if l.strip(WS)]
    return min(vals) if vals else None


# --------------------------------------------------------------------------
# Preparing the transformed text so it can replace the original bytes
# --------------------------------------------------------------------------
def detect_eol(orig: bytes, file_eol: str) -> bytes:
    if b"\r\n" in orig:
        return b"\r\n"
    if b"\n" in orig:
        return b"\n"
    return b"\r\n" if file_eol == "crlf" else b"\n"


def prepare_new(
    new_raw: bytes, orig: bytes, line_prefix: bytes, eol: bytes, reindent: str
) -> tuple[bytes, list[str]]:
    """Normalise a transformed function so it can replace `orig` byte-for-byte."""
    notes: list[str] = []

    text = new_raw.replace(b"\r\n", b"\n")
    text = re.sub(rb"\A(?:[ \t]*\n)+", b"", text)   # leading blank lines
    text = text.rstrip(b" \t\r\n")                    # trailing whitespace/newlines
    lines = text.split(b"\n")

    p = line_prefix
    p_is_ws = len(p) > 0 and p.strip(WS) == b""

    # The transform already includes the indentation of the first line? Drop it,
    # because the original line prefix stays in the file.
    if p_is_ws and lines[0].startswith(p) and not lines[0][len(p):][:1].strip(b" \t") == b"" == False:
        pass  # (kept for readability; real check below)
    if p_is_ws and lines[0].startswith(p) and lines[0][len(p):len(p) + 1] not in (b" ", b"\t", b""):
        lines[0] = lines[0][len(p):]
        notes.append("removed duplicated first-line indentation")

    # Re-indent continuation lines if the transform dedented them.
    if p_is_ws and len(lines) > 1 and reindent != "never":
        orig_lines = orig.replace(b"\r\n", b"\n").split(b"\n")
        m_raw = min_indent(orig_lines[1:])
        m_new = min_indent(lines[1:])
        do = reindent == "always"
        if reindent == "auto" and m_raw is not None and m_new is not None:
            do = (m_raw - m_new) == len(p)
        if do:
            lines[1:] = [p + l if l.strip(WS) else l for l in lines[1:]]
            notes.append("re-indented continuation lines")

    out = b"\n".join(lines)
    if eol == b"\r\n":
        out = out.replace(b"\n", b"\r\n")
    return out, notes


# --------------------------------------------------------------------------
# Edits
# --------------------------------------------------------------------------
@dataclass
class Edit:
    fn_id: int
    label: str
    start: int            # byte offsets in the original file (end exclusive)
    end: int
    old: bytes
    new: bytes
    notes: list[str] = field(default_factory=list)


def collect_edits(
    meta: dict, src: bytes, raw_dir: Path, transform_dir: Path, reindent: str,
) -> tuple[list[Edit], dict]:
    stats = {"changed": 0, "unchanged": 0, "missing": 0, "skipped": 0}
    file_eol = meta["source_file"].get("line_ending", "lf")
    edits: list[Edit] = []

    for fn in meta["functions"]:
        label = f'{fn["qualified_name"]} ({fn["raw_file"]})'
        loc = fn["location"]
        s, e = loc["start_byte"], loc["end_byte"]
        orig = src[s:e]

        if sha256(orig) != fn["sha256"]:
            warn(f"{label}: original bytes don't match recorded sha256 - skipped")
            stats["skipped"] += 1
            continue

        raw_path = raw_dir / fn["raw_file"]
        if raw_path.exists() and raw_path.read_bytes() != orig:
            warn(f"{label}: raw file differs from the source file - using the source file")

        t_path = transform_dir / fn["raw_file"]
        if not t_path.exists():
            stats["missing"] += 1
            continue

        new_raw = t_path.read_bytes()
        if not new_raw.strip():
            warn(f"{label}: transform file is empty - skipped (delete the function by hand if intended)")
            stats["skipped"] += 1
            continue

        eol = detect_eol(orig, file_eol)
        new, notes = prepare_new(
            new_raw, orig, fn.get("line_prefix", "").encode("utf-8"), eol, reindent
        )
        if new == orig:
            stats["unchanged"] += 1
            continue

        edits.append(Edit(fn["id"], label, s, e, orig, new, notes))
        stats["changed"] += 1

    # Resolve overlaps (nested functions): the outer edit wins.
    edits.sort(key=lambda x: (x.start, -x.end))
    kept: list[Edit] = []
    for ed in edits:
        if kept and ed.start < kept[-1].end:
            warn(f"{ed.label}: overlaps {kept[-1].label} - nested edit dropped (parent wins)")
            stats["changed"] -= 1
            stats["skipped"] += 1
            continue
        kept.append(ed)
    return kept, stats


# --------------------------------------------------------------------------
# Diff generation (own hunk writer so "\ No newline at end of file" is right)
# --------------------------------------------------------------------------
@dataclass
class Block:
    ls: int                 # byte start of first affected line
    le: int                 # byte end (exclusive, includes the line's "\n")
    edits: list[Edit] = field(default_factory=list)


def make_blocks(edits: list[Edit], src: bytes) -> list[Block]:
    blocks: list[Block] = []
    for ed in edits:
        ls = src.rfind(b"\n", 0, ed.start) + 1
        nl = src.find(b"\n", ed.end)
        le = len(src) if nl == -1 else nl + 1
        if blocks and ls < blocks[-1].le:        # two edits share a line -> one block
            blocks[-1].le = max(blocks[-1].le, le)
            blocks[-1].edits.append(ed)
        else:
            blocks.append(Block(ls, le, [ed]))
    return blocks


def apply_to_block(blk: Block, src: bytes) -> bytes:
    out, pos = [], blk.ls
    for ed in blk.edits:
        out.append(src[pos:ed.start])
        out.append(ed.new)
        pos = ed.end
    out.append(src[pos:blk.le])
    return b"".join(out)


def grouped_opcodes(codes: list, n: int = 3) -> Iterator[list]:
    """Same grouping algorithm as difflib.SequenceMatcher.get_grouped_opcodes."""
    if not codes:
        codes = [("equal", 0, 1, 0, 1)]
    codes = list(codes)
    if codes[0][0] == "equal":
        tag, i1, i2, j1, j2 = codes[0]
        codes[0] = tag, max(i1, i2 - n), i2, max(j1, j2 - n), j2
    if codes[-1][0] == "equal":
        tag, i1, i2, j1, j2 = codes[-1]
        codes[-1] = tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)
    nn = n + n
    group: list = []
    for tag, i1, i2, j1, j2 in codes:
        if tag == "equal" and i2 - i1 > nn:
            group.append((tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)))
            yield group
            group = []
            i1, j1 = max(i1, i2 - n), max(j1, j2 - n)
        group.append((tag, i1, i2, j1, j2))
    if group and not (len(group) == 1 and group[0][0] == "equal"):
        yield group


def fmt_range(start: int, stop: int) -> str:
    beginning, length = start + 1, stop - start
    if length == 1:
        return f"{beginning}"
    if not length:
        beginning -= 1
    return f"{beginning},{length}"


def unified_diff(src: bytes, edits: list[Edit], path_a: str, path_b: str, context: int = 3) -> bytes:
    if not edits:
        return b""
    a_lines = split_lines(src)
    b_lines: list[bytes] = []
    opcodes: list[tuple] = []
    pos = 0

    for blk in make_blocks(edits, src):
        l1 = src.count(b"\n", 0, blk.ls)
        old = split_lines(src[blk.ls:blk.le])
        l2 = l1 + len(old)
        new = split_lines(apply_to_block(blk, src))

        if l1 > pos:
            opcodes.append(("equal", pos, l1, len(b_lines), len(b_lines) + l1 - pos))
            b_lines.extend(a_lines[pos:l1])
        base_b = len(b_lines)
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            opcodes.append((tag, l1 + i1, l1 + i2, base_b + j1, base_b + j2))
        b_lines.extend(new)
        pos = l2
    if pos < len(a_lines):
        opcodes.append(("equal", pos, len(a_lines), len(b_lines), len(b_lines) + len(a_lines) - pos))
        b_lines.extend(a_lines[pos:])

    out: list[bytes] = [f"--- a/{path_a}\n".encode(), f"+++ b/{path_b}\n".encode()]

    def emit(sign: bytes, line: bytes) -> None:
        out.append(sign + line)
        if not line.endswith(b"\n"):
            out.append(b"\n\\ No newline at end of file\n")

    for group in grouped_opcodes(opcodes, context):
        first, last = group[0], group[-1]
        out.append(
            f"@@ -{fmt_range(first[1], last[2])} +{fmt_range(first[3], last[4])} @@\n".encode()
        )
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for l in a_lines[i1:i2]:
                    emit(b" ", l)
                continue
            if tag in ("replace", "delete"):
                for l in a_lines[i1:i2]:
                    emit(b"-", l)
            if tag in ("replace", "insert"):
                for l in b_lines[j1:j2]:
                    emit(b"+", l)
    return b"".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Create a git-apply diff from meta-data.json + transformed functions")
    ap.add_argument("meta", help="meta-data.json written by extract_functions.py")
    ap.add_argument("--raw", default="input/raw", help="folder with the original functions (default: raw_dir from the metadata)")
    ap.add_argument("--transform", default="input/transform", help="folder with transformed functions (default: <meta dir>/transform)")
    ap.add_argument("--source", help="original source file (default: source_file.absolute_path from the metadata)")
    ap.add_argument("--repo-path", help="path of the file inside the repo, used in the diff header "
                                        "(default: source_file.path_in_repo)")
    ap.add_argument("--repo", help="git repo root used by --check (default: source_file.repo_root)")
    ap.add_argument("-o", "--output", help="write the patch here (default: stdout)")
    ap.add_argument("--reindent", choices=["auto", "always", "never"], default="auto",
                    help="re-indent continuation lines of transformed methods (default: auto)")
    ap.add_argument("-U", "--context", type=int, default=3, help="lines of context (default: 3)")
    ap.add_argument("--check", action="store_true", help="run `git apply --check` on the result")
    ap.add_argument("--force", action="store_true", help="continue even if the source file hash changed")
    args = ap.parse_args()

    meta_path = Path(args.meta)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_dir = meta_path.resolve().parent
    sf = meta["source_file"]

    raw_dir = Path(args.raw) if args.raw else meta_dir / (meta.get("raw_dir") or "raw")
    transform_dir = Path(args.transform) if args.transform else meta_dir / "transform"
    if not transform_dir.is_dir():
        die(f"transform folder not found: {transform_dir}")

    source = Path(args.source or sf["absolute_path"])
    if not source.is_file() and not args.source and Path(sf["path"]).is_file():
        source = Path(sf["path"])
    if not source.is_file():
        die(f"source file not found: {source} (use --source)")
    src = source.read_bytes()

    if sha256(src) != sf["sha256"]:
        msg = f"{source} changed since extraction (sha256 mismatch)"
        if not args.force:
            die(msg + "; re-run extract_functions.py or pass --force")
        warn(msg)

    repo_path = args.repo_path or sf.get("path_in_repo")
    if not repo_path:
        repo_path = sf["path"]
        warn(f"file is not in a git repo according to the metadata; using '{repo_path}' in the diff header "
             "(override with --repo-path)")

    edits, stats = collect_edits(meta, src, raw_dir, transform_dir, args.reindent)
    for ed in edits:
        for n in ed.notes:
            print(f"note: {ed.label}: {n}", file=sys.stderr)

    patch = unified_diff(src, edits, repo_path, repo_path, args.context)

    print(
        f"{stats['changed']} changed, {stats['unchanged']} unchanged, "
        f"{stats['missing']} without transform file, {stats['skipped']} skipped",
        file=sys.stderr,
    )
    if not patch:
        print("no differences - nothing to write", file=sys.stderr)
        return

    if args.output:
        Path(args.output).write_bytes(patch)
        print(f"patch written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(patch)

    if args.check:
        repo = args.repo or sf.get("repo_root")
        if not repo or not Path(repo).is_dir():
            warn("--check: repo root unknown or missing (use --repo); skipped")
            return
        r = subprocess.run(["git", "-C", repo, "apply", "--check", "-"], input=patch,
                           capture_output=True)
        if r.returncode == 0:
            print("git apply --check: OK", file=sys.stderr)
        else:
            print("git apply --check: FAILED\n" + r.stderr.decode(errors="replace"), file=sys.stderr)
            sys.exit(3)


if __name__ == "__main__":
    main()