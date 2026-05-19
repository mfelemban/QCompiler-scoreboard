"""Wrapper: invokes Zining's peephole.optimize_circuit on INPUT.qasm.

We use the peephole engine only — the full v13 beam search requires a v12
baseline seed and is not portable to arbitrary benchmarks.
"""
import sys
from pathlib import Path
import qiskit.qasm3

ROOT = Path("/Users/mfelemban/Dropbox/KFUPM/Teaching/T252/COE530/Project/Groups/Zining")
sys.path.insert(0, str(ROOT))

from peephole import optimize_circuit  # noqa: E402

inp, out = sys.argv[1], sys.argv[2]
qc = qiskit.qasm3.load(inp)
opt = optimize_circuit(qc, mode="full")
with open(out, "w") as f:
    qiskit.qasm3.dump(opt, f)
print(f"zining: wrote {out}")
