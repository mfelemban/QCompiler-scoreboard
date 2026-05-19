"""Wrapper: runs Hanbash's notebook pipeline on INPUT.qasm."""
import os, re, sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
CONVERTED = Path(__file__).parent.parent / "converted" / "hanbash.py"
inp, out = sys.argv[1], sys.argv[2]

src = CONVERTED.read_text()
src = re.sub(r"^\s*%[a-zA-Z]+.*$", "", src, flags=re.MULTILINE)
src = re.sub(r"^(.*\.draw\(.*\))$", r"# stripped: \1", src, flags=re.MULTILINE)
src = src.replace(
    'BENCHMARK_PATH = "benchmark.qasm"', f'BENCHMARK_PATH = {inp!r}'
)
src = src.replace(
    'OUTPUT_PATH = "submission.qasm"', f'OUTPUT_PATH = {out!r}'
)

g = {"__name__": "__hanbash_wrapper__", "__file__": str(CONVERTED)}
exec(compile(src, str(CONVERTED), "exec"), g)
print(f"hanbash: wrote {out}")
