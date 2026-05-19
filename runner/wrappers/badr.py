"""Wrapper: invokes Badr's pipeline on INPUT.qasm.

Replicates the __main__ block of Project_v11_clean.ipynb but with paths
from argv and num_qubits read from the input circuit.
"""
import sys
from pathlib import Path
from qiskit import qasm3, QuantumCircuit

CONVERTED = Path(__file__).parent.parent / "converted"
sys.path.insert(0, str(CONVERTED))
from badr import run_virtual_swap_processor_in_memory, optimize_circuit_v4  # noqa: E402

inp, out = sys.argv[1], sys.argv[2]
orig = qasm3.load(inp)
num_qubits = orig.num_qubits

processed_qasm_str, _ = run_virtual_swap_processor_in_memory(inp, num_qubits=num_qubits)
qc_processed = qasm3.loads(processed_qasm_str)
gates = []
for instruction in qc_processed.data:
    gate_name = instruction.operation.name
    qubits = [q._index for q in instruction.qubits]
    params = [float(p) for p in instruction.operation.params]
    gates.append([gate_name, qubits, params])

final_circuit, final_phase = optimize_circuit_v4(gates, num_qubits=num_qubits)

optimized_qc = QuantumCircuit(num_qubits, global_phase=final_phase)
for gate_name, qubits, params in final_circuit:
    gate_func = getattr(optimized_qc, gate_name)
    if params:
        gate_func(*params, *qubits)
    else:
        gate_func(*qubits)

with open(out, "w") as f:
    qasm3.dump(optimized_qc, f)
print(f"badr: wrote {out}")
