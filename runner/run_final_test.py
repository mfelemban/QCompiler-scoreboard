"""Drive all groups' optimizers against the 5 final-test benchmarks.

For each (group, benchmark) pair:
  - Spawn the group's wrapper as a subprocess with a timeout
  - The wrapper writes an optimized QASM file
  - Re-load it, compute metrics + score, verify unitary equivalence
  - Upsert the result into scoreboard.db

Run from the scoreboard/ directory:
    python runner/run_final_test.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Make scoreboard imports work no matter where this is invoked from.
SCOREBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCOREBOARD_DIR))

from db import get_weights, init_db, upsert_final_submission  # noqa: E402
from scoring import compute_metrics, compute_score, load_circuit, verify_equivalence  # noqa: E402

RUNNER_DIR = SCOREBOARD_DIR / "runner"
WRAPPERS_DIR = RUNNER_DIR / "wrappers"
OUTPUTS_DIR = RUNNER_DIR / "outputs"
BENCHMARK_DIR = SCOREBOARD_DIR / "final_benchmarks"
DB_PATH = SCOREBOARD_DIR / "scoreboard.db"
VENV_PY = SCOREBOARD_DIR / ".venv" / "bin" / "python"

PER_RUN_TIMEOUT = int(os.environ.get("PER_RUN_TIMEOUT", "240"))  # seconds

GROUPS = [
    "abdulrahman",
    "badr",
    "fahad",
    "hanbash",
    "ibraheem",
    "mutab",
    "rawan",
    "ryadh",
    "zahra",
    "zining",
]

DISPLAY_NAMES = {
    "abdulrahman": "Abdulrahman",
    "badr": "Badr",
    "fahad": "Fahad",
    "hanbash": "Hanbash",
    "ibraheem": "Ibraheem",
    "mutab": "Mutab and Team",
    "rawan": "Rawan and Team",
    "ryadh": "Ryadh and Team",
    "zahra": "Zahra and Team",
    "zining": "Zining",
}

BENCHMARKS = {
    1: BENCHMARK_DIR / "circuit_1_very_easy.qasm",
    2: BENCHMARK_DIR / "circuit_2_easy.qasm",
    3: BENCHMARK_DIR / "circuit_3_medium.qasm",
    4: BENCHMARK_DIR / "circuit_4_hard.qasm",
    5: BENCHMARK_DIR / "circuit_5_very_hard.qasm",
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def run_one(group: str, circuit_number: int, conn) -> dict:
    wrapper = WRAPPERS_DIR / f"{group}.py"
    benchmark = BENCHMARKS[circuit_number]
    out_path = OUTPUTS_DIR / f"{group}_circuit_{circuit_number}.qasm"
    log_path = OUTPUTS_DIR / f"{group}_circuit_{circuit_number}.log"

    if not wrapper.exists():
        return {"status": "skip", "msg": f"missing wrapper {wrapper.name}"}

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env["PYTHONUNBUFFERED"] = "1"

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [str(VENV_PY), str(wrapper), str(benchmark), str(out_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=PER_RUN_TIMEOUT,
            env=env,
            cwd=str(SCOREBOARD_DIR),
        )
        elapsed = time.monotonic() - t0
        log_path.write_bytes(proc.stdout)
        if proc.returncode != 0:
            return {
                "status": "error",
                "msg": f"exit {proc.returncode}; see {log_path.name}",
                "elapsed": elapsed,
            }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - t0
        log_path.write_bytes(exc.stdout or b"")
        return {
            "status": "timeout",
            "msg": f"hit {PER_RUN_TIMEOUT}s timeout",
            "elapsed": elapsed,
        }
    except Exception as exc:
        return {"status": "error", "msg": f"spawn failed: {exc}"}

    if not out_path.exists():
        return {
            "status": "error",
            "msg": f"wrapper produced no output file; see {log_path.name}",
            "elapsed": elapsed,
        }

    try:
        text = out_path.read_text()
        qc_opt = load_circuit(text)
    except Exception as exc:
        return {
            "status": "error",
            "msg": f"failed to parse output: {exc}",
            "elapsed": elapsed,
        }

    metrics = compute_metrics(qc_opt)
    weights = get_weights(conn)
    score = compute_score(metrics, **weights)

    try:
        benchmark_qc = load_circuit(benchmark.read_text())
        verified, verify_msg = verify_equivalence(qc_opt, benchmark_qc)
    except Exception as exc:
        verified, verify_msg = False, f"verify exception: {exc}"

    upsert_final_submission(
        conn,
        team_name=DISPLAY_NAMES[group],
        circuit_number=circuit_number,
        submitted_at=now_utc_iso(),
        qubit_count=metrics["qubit_count"],
        depth=metrics["depth"],
        gate_count=metrics["gate_count"],
        score=score,
        w1=weights["w1"],
        w2=weights["w2"],
        w3=weights["w3"],
        filename=out_path.name,
        verified=1 if verified else 0,
        verify_message=verify_msg,
    )
    return {
        "status": "ok" if verified else "ok-unverified",
        "qubits": metrics["qubit_count"],
        "depth": metrics["depth"],
        "gates": metrics["gate_count"],
        "score": score,
        "verified": verified,
        "verify_msg": verify_msg,
        "elapsed": elapsed,
    }


def main():
    conn = init_db(DB_PATH)
    args = sys.argv[1:]
    only_circuits = set()
    only_groups = set()
    for a in args:
        if a.startswith("c") and a[1:].isdigit():
            only_circuits.add(int(a[1:]))
        else:
            only_groups.add(a)
    summary = []
    for group in GROUPS:
        if only_groups and group not in only_groups:
            continue
        for circuit_number in BENCHMARKS:
            if only_circuits and circuit_number not in only_circuits:
                continue
            print(f"\n[{group} / circuit {circuit_number}] ...", flush=True)
            try:
                r = run_one(group, circuit_number, conn)
            except Exception:
                traceback.print_exc()
                r = {"status": "error", "msg": "uncaught exception in runner"}
            summary.append((group, circuit_number, r))
            if r["status"].startswith("ok"):
                flag = "OK " if r["status"] == "ok" else "?? "
                print(
                    f"  {flag}qubits={r['qubits']:<3d} depth={r['depth']:<4d} "
                    f"gates={r['gates']:<4d} score={r['score']:.2f} "
                    f"({r['elapsed']:.1f}s)",
                    flush=True,
                )
            else:
                print(f"  !! {r['status']}: {r.get('msg', '')}", flush=True)

    print("\n\n=== SUMMARY ===")
    print(f"{'Group':<20} {'C1':>10} {'C2':>10} {'C3':>10} {'C4':>10} {'C5':>10}")
    by_group = {}
    for group, c, r in summary:
        by_group.setdefault(group, {})[c] = r
    for group in GROUPS:
        if group not in by_group:
            continue
        row = [DISPLAY_NAMES[group].ljust(20)]
        for c in (1, 2, 3, 4, 5):
            r = by_group[group].get(c)
            if r is None or not r["status"].startswith("ok"):
                cell = r["status"][:9] if r else "—"
            else:
                cell = f"{r['score']:.1f}"
            row.append(cell.rjust(10))
        print("".join(row))


if __name__ == "__main__":
    main()
