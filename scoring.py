from __future__ import annotations

from typing import Tuple

from qiskit import QuantumCircuit
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.qasm3 import loads as qasm3_loads
from qiskit.quantum_info import Operator

_SKIP = {"barrier", "measure", "delay", "reset"}


def load_circuit(text: str) -> QuantumCircuit:
    errors = []
    for name, fn in (("QASM 3", qasm3_loads), ("QASM 2", qasm2_loads)):
        try:
            return fn(text)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise ValueError("Could not parse circuit.\n" + "\n".join(errors))


_PRIMITIVE_GATES = {
    "u", "u1", "u2", "u3", "p", "id",
    "x", "y", "z", "h", "s", "sdg", "t", "tdg", "sx", "sxdg",
    "rx", "ry", "rz", "r",
    "cx", "cz", "cy", "ch", "cp", "crx", "cry", "crz", "cu", "cu1", "cu3",
    "swap", "iswap", "ccx", "cswap", "rxx", "ryy", "rzz", "rzx",
    "global_phase",
}


def fully_decompose(qc: QuantumCircuit, max_iters: int = 12) -> QuantumCircuit:
    """Decompose custom/composite gates recursively until only primitives remain.

    Some groups' optimizers wrap their output in custom QASM gate definitions
    (e.g. clifford_3q blocks, consolidated 2q unitaries). Qiskit's depth/size
    methods count those as a single instruction, which would under-report gate
    counts and depth. We unfold them so all groups are measured the same way.
    """
    cur = qc
    for _ in range(max_iters):
        names = {ci.operation.name for ci in cur.data}
        custom = names - _PRIMITIVE_GATES - _SKIP
        if not custom:
            return cur
        cur = cur.decompose(list(custom))
    return cur


def compute_metrics(qc: QuantumCircuit) -> dict:
    qc = fully_decompose(qc)
    gate_count = sum(1 for ci in qc.data if ci.operation.name not in _SKIP)
    depth = qc.depth(filter_function=lambda ci: ci.operation.name not in _SKIP)
    return {
        "qubit_count": qc.num_qubits,
        "depth": depth,
        "gate_count": gate_count,
    }


def compute_score(metrics: dict, w1: float, w2: float, w3: float) -> float:
    return (
        w1 * metrics["qubit_count"]
        + w2 * metrics["depth"]
        + w3 * metrics["gate_count"]
    )


def verify_equivalence(
    submitted: QuantumCircuit, benchmark: QuantumCircuit
) -> Tuple[bool, str]:
    if submitted.num_qubits != benchmark.num_qubits:
        return False, (
            f"Submitted circuit has {submitted.num_qubits} qubits; benchmark has "
            f"{benchmark.num_qubits}. Automatic unitary equivalence requires the same "
            "qubit count. Qubit-reuse or ancilla-reduction optimizations must be "
            "verified manually by the instructor via the admin panel."
        )
    for ci in submitted.data:
        if ci.operation.name in ("measure", "reset"):
            return False, (
                f"Submitted circuit contains a '{ci.operation.name}' instruction, which "
                "breaks unitary equivalence. Remove measurements/resets to pass the "
                "automatic check (or request manual verification)."
            )
    try:
        u_sub = Operator(submitted)
        u_ref = Operator(benchmark)
    except Exception as exc:
        return False, f"Could not construct unitary operator: {exc}"
    if u_sub.equiv(u_ref):
        return True, "Functionally equivalent to benchmark (unitary match up to global phase)."
    return False, "Circuit unitary does NOT match the benchmark. Re-check your optimizations."
