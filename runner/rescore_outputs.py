"""Re-score every existing wrapper output without re-running optimizers.

Reads runner/outputs/*.qasm, recomputes (fully-decomposed) metrics, and
upserts each (team, circuit) into the DB. Use after changing scoring.py.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SCOREBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCOREBOARD_DIR))

from db import get_weights, init_db, upsert_final_submission  # noqa: E402
from scoring import compute_metrics, compute_score, load_circuit, verify_equivalence  # noqa: E402

SKIP_REVERIFY = "--skip-verify" in sys.argv
if SKIP_REVERIFY:
    sys.argv.remove("--skip-verify")

OUTPUTS_DIR = SCOREBOARD_DIR / "runner" / "outputs"
BENCHMARK_DIR = SCOREBOARD_DIR / "final_benchmarks"
DB_PATH = SCOREBOARD_DIR / "scoreboard.db"

BENCHMARK_FILES = {
    1: BENCHMARK_DIR / "circuit_1_very_easy.qasm",
    2: BENCHMARK_DIR / "circuit_2_easy.qasm",
    3: BENCHMARK_DIR / "circuit_3_medium.qasm",
    4: BENCHMARK_DIR / "circuit_4_hard.qasm",
    5: BENCHMARK_DIR / "circuit_5_very_hard.qasm",
}

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


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def main():
    conn = init_db(DB_PATH)
    weights = get_weights(conn)

    files = sorted(OUTPUTS_DIR.glob("*_circuit_*.qasm"))
    for path in files:
        stem = path.stem  # e.g. "ryadh_circuit_3"
        try:
            group, _, circ = stem.rpartition("_circuit_")
            circuit_number = int(circ)
        except ValueError:
            continue
        team = DISPLAY_NAMES.get(group, group)
        benchmark = BENCHMARK_FILES.get(circuit_number)
        if benchmark is None:
            continue

        try:
            qc = load_circuit(path.read_text())
        except Exception as exc:
            print(f"!! parse fail {path.name}: {exc}")
            continue

        metrics = compute_metrics(qc)
        score = compute_score(metrics, **weights)

        if SKIP_REVERIFY:
            # Trust the existing DB verified flag (set by the original runner).
            row = conn.execute(
                "SELECT verified, verify_message FROM final_submissions "
                "WHERE team_name=? AND circuit_number=?",
                (team, circuit_number),
            ).fetchone()
            if row is None:
                verified, verify_msg = False, "no prior verify record"
            else:
                verified = bool(row[0])
                verify_msg = row[1] or ""
        else:
            try:
                bench = load_circuit(benchmark.read_text())
                verified, verify_msg = verify_equivalence(qc, bench)
            except Exception as exc:
                verified, verify_msg = False, f"verify exception: {exc}"

        upsert_final_submission(
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
            filename=path.name,
            verified=1 if verified else 0,
            verify_message=verify_msg,
        )
        flag = "OK " if verified else "?? "
        print(
            f"{flag}{team:<20s} c{circuit_number} "
            f"q={metrics['qubit_count']:<3d} d={metrics['depth']:<4d} "
            f"g={metrics['gate_count']:<4d} score={score:.2f}"
        )


if __name__ == "__main__":
    main()
