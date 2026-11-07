import argparse
from pathlib import Path

from newnat.utils import *
from newnat.preprocess import main as preprocess
from newnat.transform import main as transform

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract functions from one file into raw files + meta-data.json"
    )
    ap.add_argument("file", help="source file to parse")
    ap.add_argument("-o", "--out-dir", default="input/raw", help="folder for raw functions (default: raw)")
    ap.add_argument("--meta", default=None,
                    help="metadata path (default: meta-data.json next to the output folder)")
    ap.add_argument("--include-anonymous", action="store_true",
                    help="include anonymous functions/callbacks")
    args = ap.parse_args()

    path = Path(args.file)
    print("[*] Preprocess...")
    funcs, lang, src = preprocess(
        path, 
        out_dir=OUTPUT_DIR, 
        meta_path=OUTPUT_DIR / "metadata.json"
    )
    
    print("[*] Transforming...")
    funcs.reverse()
    transformed_src, modified_code, success = transform(funcs, src, lang)
    open("output_bytes", "wb").write(transformed_src)
    open("output.py", "w").write(modified_code)
    print(success)

if __name__ == "__main__":
    main()
    
    