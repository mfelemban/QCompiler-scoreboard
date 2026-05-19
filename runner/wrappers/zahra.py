"""Wrapper: runs Zahra's notebook pipeline on INPUT.qasm.

Zahra's pipeline uses a hand-crafted Manual.qasm as input. For the runner,
we use the input benchmark itself in place of Manual.qasm. Intermediate
filenames are redirected to temp paths.
"""
import os, re, sys, tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
CONVERTED = Path(__file__).parent.parent / "converted" / "zahra.py"
inp, out = sys.argv[1], sys.argv[2]
tmpdir = tempfile.mkdtemp(prefix="zahra_")
tmp1 = os.path.join(tmpdir, "stage1.qasm")
tmp2 = os.path.join(tmpdir, "stage2.qasm")

src = CONVERTED.read_text()
src = re.sub(r"^\s*!.*$", "", src, flags=re.MULTILINE)        # strip !pip lines
src = re.sub(r"^\s*%[a-zA-Z]+.*$", "", src, flags=re.MULTILINE)
src = re.sub(r"^(.*\.draw\(.*\))$", r"# stripped: \1", src, flags=re.MULTILINE)
# Cells 19-20 reference an absolute path on the team's laptop. Drop them.
cell19_idx = src.find("# === cell 19 ===")
if cell19_idx != -1:
    src = src[:cell19_idx]
# Path redirections
src = src.replace('"benchmark_circuit.qasm"', repr(inp))
src = src.replace('"Manual.qasm"', repr(inp))
src = src.replace('"optimized.qasm"', repr(tmp1))
src = src.replace('"second_optimized.qasm"', repr(tmp2))
src = src.replace('"final_optimized.qasm"', repr(out))

g = {"__name__": "__zahra_wrapper__", "__file__": str(CONVERTED)}
exec(compile(src, str(CONVERTED), "exec"), g)
print(f"zahra: wrote {out}")
