"""Wrapper: runs Fahad's procedural notebook pipeline on INPUT.qasm.

Reads the converted notebook source, strips Jupyter magics + plot calls,
patches QASM_PATH/OUT_PATH to argv, then execs it. The demo cells at the
end of the notebook still run (they use their own variable names and
don't affect the main `working` circuit).
"""
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

CONVERTED = Path(__file__).parent.parent / "converted" / "fahad.py"

inp, out = sys.argv[1], sys.argv[2]

src = CONVERTED.read_text()
# Strip Jupyter line/cell magics
src = re.sub(r"^\s*%[a-zA-Z]+.*$", "", src, flags=re.MULTILINE)
# Skip .draw() calls — they return matplotlib figures; safe to keep but
# replace with no-ops to avoid headless backend warnings.
src = re.sub(r"^(.*\.draw\(.*\))$", r"# stripped: \1", src, flags=re.MULTILINE)
# Patch hardcoded paths
src = src.replace(
    'QASM_PATH = "benchmark_circuit.qasm"',
    f'QASM_PATH = {inp!r}',
)
src = src.replace(
    'OUT_PATH = "benchmark_circuit_optimized.qasm"',
    f'OUT_PATH = {out!r}',
)

g = {"__name__": "__fahad_wrapper__", "__file__": str(CONVERTED)}
exec(compile(src, str(CONVERTED), "exec"), g)
print(f"fahad: wrote {out}")
