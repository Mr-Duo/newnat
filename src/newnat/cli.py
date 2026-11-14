import argparse
import tempfile
from datetime import datetime
from pathlib import Path

import yaml
import difflib
from importlib.metadata import version
from copy import deepcopy

from newnat.preprocess import main as preprocess
from newnat.transform import TRANSFORM, main as run_transform

DEFAULTS = {
    "result_dir": "jobs",
    "job_name": None,
    "include_anonymous": False,
    "transform": ["block_swap"],       # falls back to ["block_swap"]
    "continuous": False,
    "diff": False,
}
JOB_KEYS = set(DEFAULTS) | {"file"}


def load(path: Path, out_dir: Path, meta_path: Path):
    """Preprocess a file and return (funcs in reverse order, language, source bytes)."""
    funcs, lang, src = preprocess(path, out_dir=out_dir, meta_path=meta_path)
    # Reversed so later functions are transformed first and earlier byte offsets stay valid.
    return list(reversed(funcs)), lang, src


def save_result(src: bytes, input_path: Path, result_root: Path, label: str, original: bytes | None = None) -> Path:
    """Save to <result_root>/<stem>_<label>_<stamp>/<original filename>."""
    out_dir = result_root / f"{input_path.stem}_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / input_path.name
    out_file.write_bytes(src)
    
    if original is not None:
        diff_text = make_unified_diff(original, src, input_path.name)
        (out_dir / f"{input_path.name}.patch").write_text(diff_text, encoding="utf-8")

    return out_file

def make_unified_diff(original: bytes, transformed: bytes, name: str) -> str:
    """Return a unified diff (original -> transformed) as a string."""
    return "".join(
        difflib.unified_diff(
            original.decode("utf-8", errors="replace").splitlines(keepends=True),
            transformed.decode("utf-8", errors="replace").splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )


def run_job(cfg: dict) -> None:
    """Run one job: one input file, one or more transforms."""
    transforms = cfg["transform"] or ["block_swap"]
    if isinstance(transforms, str):
        transforms = [transforms]
    unknown = [t for t in transforms if t not in TRANSFORM]
    if unknown:
        raise SystemExit(f"Unknown transform(s): {unknown}. Choose from: {sorted(TRANSFORM)}")

    stamp = cfg["job_name"] if cfg["job_name"] else datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
    path = Path(cfg["file"])
    root_path = Path(cfg["result_dir"]) / stamp / f"{path.name.replace('.', '__')}"
    raw_dir = root_path / "original" / "raw"
    meta_path = root_path / "original" / "meta-data.json"
    result_root = root_path / "transformed"
    
    print(f"[*] Preprocess {path}...")
    funcs, lang, src = load(path, raw_dir, meta_path)
    original_src = deepcopy(src) if cfg["diff"] else None

    if not cfg["continuous"]:
        # Each transform is applied independently to the original source.
        for t in transforms:
            print(f"[*] Transforming with {t}...")
            new_src, _, success = run_transform(funcs, src, lang, t)
            out = save_result(new_src, path, result_root, t, original_src)
            print(f"    success={success} -> {out}")
        return

    # Continuous: each step feeds the next. Offsets change after every transform,
    # so the intermediate result is re-preprocessed to get fresh function info.
    cur_src = src
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, t in enumerate(transforms):
            if i > 0:
                tmp_file = tmp / path.name
                tmp_file.write_bytes(cur_src)
                funcs, lang, cur_src = load(tmp_file, tmp / "raw", tmp / "meta-data.json")

            print(f"[*] Transforming ({i + 1}/{len(transforms)}) with {t}...")
            cur_src, _, success = run_transform(funcs, cur_src, lang, t)

            label = "-".join(transforms[: i + 1])
            out = save_result(cur_src, path, result_root, label, original_src)
            print(f"    success={success} -> {out}")
            if not success:
                print(f"    [!] {t} made no changes; continuing with unchanged source")


def load_config(config_path: Path) -> tuple[dict, list[dict]]:
    """Return (top-level defaults, list of per-run overrides) from a YAML file."""
    data = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{config_path}: top level must be a mapping")

    runs = data.pop("runs", None)
    if runs is None:
        runs = [{}]
    elif not isinstance(runs, list) or not all(isinstance(r, dict) for r in runs):
        raise SystemExit(f"{config_path}: 'runs' must be a list of mappings")

    for block in [data, *runs]:
        bad = set(block) - JOB_KEYS
        if bad:
            raise SystemExit(f"{config_path}: unknown key(s) {sorted(bad)}. Allowed: {sorted(JOB_KEYS)}")
    return data, runs


def build_jobs(args: argparse.Namespace) -> list[dict]:
    """Merge precedence (low -> high): built-in defaults, YAML top level, YAML run, CLI flags."""
    cli = {k: v for k, v in vars(args).items() if k != "config" and v is not None}

    base, runs = {}, [{}]
    if args.config:
        base, runs = load_config(Path(args.config))

    jobs = []
    for run in runs:
        cfg = {**DEFAULTS, **base, **run, **cli}
        files = cfg.get("file")
        if not files:
            raise SystemExit("No input file: pass FILE on the command line or set 'file' in the config.")
        # 'file' may be a single path or a list of paths.
        for f in ([files] if isinstance(files, str) else files):
            jobs.append({**cfg, "file": f})
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract functions from a file, apply transforms, and save the results."
    )
    ap.add_argument("file", nargs="?", default=None,
                    help="source file to parse (optional if set in --config)")
    ap.add_argument("-v", "--version", action="version", 
                    version=f"%(prog)s {version('newnat')}")
    ap.add_argument("-c", "--config", default=None, metavar="run.yaml",
                    help="YAML config file; explicit CLI flags override its values")
    ap.add_argument("--result-dir", default=None,
                    help=f"root folder for outputs (default: {DEFAULTS['result_dir']})")
    ap.add_argument("-j", "--job-name", default=None,
                    help=f"job name for output of jobs (default: timestamp YYYY-MM-DD__hh-mm-ss)")
    ap.add_argument("--include-anonymous", action="store_true", default=None,
                    help="include anonymous functions/callbacks")
    ap.add_argument("-t", "--transform", nargs="+", action="extend", default=None,
                    choices=sorted(TRANSFORM), metavar="NAME",
                    help=f"one or more transforms ({', '.join(sorted(TRANSFORM))}); "
                         "may be repeated. Default: block_swap")
    ap.add_argument("--continuous", action="store_true", default=None,
                    help="chain transforms: the output of t1 is the input of t2, and so on")
    ap.add_argument("--diff", action="store_true", default=None,
                help="also write a unified diff between each step's output and the original file")
    args = ap.parse_args()

    jobs = build_jobs(args)
    for n, job in enumerate(jobs, 1):
        job_type = "chained" if job['continuous'] else "separated"
        print(f"=== Job {n}/{len(jobs)}: {job['file']} - Type: {job_type} ===")
        run_job(job)
        print("\n")

if __name__ == "__main__":
    main()