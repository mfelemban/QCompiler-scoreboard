"""CLI for the instructor to record final-test scores.

Usage:
    python submit_final.py --team TEAM --circuit N --file path/to/optimized.qasm
    python submit_final.py --batch path/to/dir            # see --help

Each (team, circuit_number) pair is unique: re-running overwrites the prior score.
The score formula uses whatever weights are currently configured in the DB.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from db import get_weights, init_db, upsert_final_submission
from scoring import (
    compute_metrics,
    compute_score,
    load_circuit,
    verify_equivalence,
)

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "scoreboard.db"
BENCHMARK_DIR = APP_DIR / "final_benchmarks"

BENCHMARK_FILES = {
    1: BENCHMARK_DIR / "circuit_1_very_easy.qasm",
    2: BENCHMARK_DIR / "circuit_2_easy.qasm",
    3: BENCHMARK_DIR / "circuit_3_medium.qasm",
    4: BENCHMARK_DIR / "circuit_4_hard.qasm",
    5: BENCHMARK_DIR / "circuit_5_very_hard.qasm",
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_benchmark(circuit_number: int):
    path = BENCHMARK_FILES.get(circuit_number)
    if path is None or not path.exists():
        raise FileNotFoundError(
            f"No benchmark file for circuit {circuit_number} (expected {path})."
        )
    return load_circuit(path.read_text())


def score_one(
    conn,
    team: str,
    circuit_number: int,
    file_path: Path,
    skip_verify: bool,
) -> dict:
    text = file_path.read_text()
    qc = load_circuit(text)
    metrics = compute_metrics(qc)
    weights = get_weights(conn)
    score = compute_score(metrics, **weights)

    if skip_verify:
        verified, verify_msg = True, "Verification skipped (instructor)."
    else:
        benchmark = load_benchmark(circuit_number)
        verified, verify_msg = verify_equivalence(qc, benchmark)

    sid = upsert_final_submission(
        conn,
        team_name=team,
        circuit_number=circuit_number,
        submitted_at=now_utc_iso(),
        qubit_count=metrics["qubit_count"],
        depth=metrics["depth"],
        gate_count=metrics["gate_count"],
        score=score,
        w1=weights["w1"],
        w2=weights["w2"],
        w3=weights["w3"],
        filename=file_path.name,
        verified=1 if verified else 0,
        verify_message=verify_msg,
    )
    return {
        "id": sid,
        "team": team,
        "circuit": circuit_number,
        "qubits": metrics["qubit_count"],
        "depth": metrics["depth"],
        "gates": metrics["gate_count"],
        "score": score,
        "verified": verified,
        "verify_message": verify_msg,
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    one = sub.add_parser("one", help="Submit a single circuit for one team.")
    one.add_argument("--team", required=True, help="Team / group name.")
    one.add_argument(
        "--circuit",
        type=int,
        choices=[1, 2, 3, 4, 5],
        required=True,
        help="Benchmark circuit number (1=very easy ... 5=very hard).",
    )
    one.add_argument("--file", required=True, type=Path, help="Optimized QASM file.")
    one.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip unitary-equivalence check (use for qubit-reuse optimizations).",
    )

    batch = sub.add_parser(
        "batch",
        help=(
            "Submit a folder containing files named "
            "{team}_circuit{N}.qasm — N in 1..5."
        ),
    )
    batch.add_argument("--dir", required=True, type=Path)
    batch.add_argument("--skip-verify", action="store_true")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    conn = init_db(DB_PATH)

    if args.cmd == "one":
        result = score_one(
            conn, args.team, args.circuit, args.file, args.skip_verify
        )
        _print_result(result)
        return 0

    if args.cmd == "batch":
        directory: Path = args.dir
        if not directory.is_dir():
            print(f"Not a directory: {directory}", file=sys.stderr)
            return 1
        files = sorted(directory.glob("*_circuit*.qasm"))
        if not files:
            print(f"No files matching *_circuit*.qasm in {directory}", file=sys.stderr)
            return 1
        for f in files:
            stem = f.stem
            try:
                team, circ_part = stem.rsplit("_circuit", 1)
                circuit_number = int(circ_part)
            except ValueError:
                print(f"Skipping (bad name): {f.name}", file=sys.stderr)
                continue
            if circuit_number not in BENCHMARK_FILES:
                print(
                    f"Skipping {f.name}: circuit {circuit_number} out of range.",
                    file=sys.stderr,
                )
                continue
            try:
                result = score_one(
                    conn, team, circuit_number, f, args.skip_verify
                )
                _print_result(result)
            except Exception as exc:
                print(f"FAILED {f.name}: {exc}", file=sys.stderr)
        return 0

    return 1


def _print_result(r: dict) -> None:
    flag = "OK " if r["verified"] else "!! "
    print(
        f"{flag}team={r['team']:<20s} circuit={r['circuit']} "
        f"qubits={r['qubits']:<3d} depth={r['depth']:<4d} "
        f"gates={r['gates']:<4d} score={r['score']:.2f}  "
        f"({r['verify_message']})"
    )


if __name__ == "__main__":
    sys.exit(main())
