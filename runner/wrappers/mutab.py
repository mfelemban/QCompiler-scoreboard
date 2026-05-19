"""Wrapper: invokes Mutab's QuantumCircuitOptimizer.optimize_greedy on INPUT.qasm.

Uses the greedy strategy (fastest deterministic option). The evolutionary
search in their __main__ is far too slow for the runner budget.
"""
import sys
from pathlib import Path
import qiskit.qasm3

CONVERTED = Path(__file__).parent.parent / "converted"
sys.path.insert(0, str(CONVERTED))
from mutab import QuantumCircuitOptimizer  # noqa: E402

inp, out = sys.argv[1], sys.argv[2]
opt = QuantumCircuitOptimizer(w1=10, w2=1, w3=1)
opt.load_qasm_file(inp)
opt.optimize_greedy()
optimized = opt.optimized_circuit
with open(out, "w") as f:
    qiskit.qasm3.dump(optimized, f)
print(f"mutab: wrote {out}")
