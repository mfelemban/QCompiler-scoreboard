from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from db import (
    all_submissions,
    best_per_team,
    delete_submission,
    get_weights,
    init_db,
    insert_submission,
    rescore_all,
    set_verified,
    set_weights,
)
from scoring import compute_metrics, compute_score, load_circuit, verify_equivalence

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "scoreboard.db"
BENCHMARK_PATH = APP_DIR / "benchmark_circuit.qasm"

st.set_page_config(
    page_title="COE 530 Scoreboard",
    page_icon="⚛️",
    layout="wide",
)


@st.cache_resource
def get_db():
    return init_db(DB_PATH)


@st.cache_resource
def get_benchmark():
    if not BENCHMARK_PATH.exists():
        return None
    return load_circuit(BENCHMARK_PATH.read_text())


def get_secret(key: str, default: str) -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


CLASS_PASSWORD = get_secret("class_password", "coe530")
ADMIN_PASSWORD = get_secret("admin_password", "admin")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def page_scoreboard(conn):
    st.title("⚛️ COE 530 — Quantum Circuit Optimization Scoreboard")
    st.caption(
        "Term 252 · King Fahd University of Petroleum and Minerals · "
        "Computer Engineering Department"
    )

    weights = get_weights(conn)
    st.markdown(
        f"**Score formula:** `Score = {weights['w1']:g} · QubitCount + "
        f"{weights['w2']:g} · Depth + {weights['w3']:g} · GateCount` — "
        "*lower is better.*"
    )

    rows = best_per_team(conn)
    if not rows:
        st.info("No verified submissions yet — be the first team on the board!")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    df.insert(0, "Rank", range(1, len(df) + 1))
    display = df[
        ["Rank", "team_name", "qubit_count", "depth", "gate_count", "score", "submitted_at"]
    ].rename(
        columns={
            "team_name": "Team",
            "qubit_count": "Qubits",
            "depth": "Depth",
            "gate_count": "Gates",
            "score": "Score",
            "submitted_at": "Submitted",
        }
    )
    display["Score"] = display["Score"].map(lambda x: f"{x:.2f}")
    st.dataframe(display, hide_index=True, use_container_width=True)

    winner = df.iloc[0]
    st.success(
        f"🏆 **Current leader:** {winner['team_name']} — score {winner['score']:.2f} "
        f"({int(winner['qubit_count'])} qubits, depth {int(winner['depth'])}, "
        f"{int(winner['gate_count'])} gates)"
    )


def page_submit(conn):
    st.title("📤 Submit Your Optimized Circuit")

    benchmark = get_benchmark()
    if benchmark is None:
        st.error("Benchmark circuit is not yet available. Check back after instructor setup.")
        return

    bench_metrics = compute_metrics(benchmark)
    st.markdown(
        f"**Benchmark:** {bench_metrics['qubit_count']} qubits, "
        f"depth {bench_metrics['depth']}, {bench_metrics['gate_count']} gates. "
        "Submit your optimized version as OpenQASM 2.0 or 3.0."
    )
    st.markdown(
        "> Qiskit users can export via `qiskit.qasm3.dumps(qc)` or "
        "`qiskit.qasm2.dumps(qc)` and upload the text file."
    )

    with st.form("submit_form", clear_on_submit=False):
        team_name = st.text_input("Team name", max_chars=80, placeholder="e.g., Team Hadamard")
        class_password = st.text_input("Class password", type="password")
        file = st.file_uploader("Circuit file (.qasm / .txt)", type=["qasm", "txt", "inc"])
        submitted = st.form_submit_button("Score my circuit", type="primary")

    if not submitted:
        return

    team_name = (team_name or "").strip()
    if not team_name:
        st.error("Team name is required.")
        return
    if class_password != CLASS_PASSWORD:
        st.error("Class password is incorrect.")
        return
    if file is None:
        st.error("Please upload a circuit file.")
        return

    try:
        text = file.read().decode("utf-8")
    except UnicodeDecodeError:
        st.error("File must be UTF-8 text.")
        return

    try:
        qc = load_circuit(text)
    except Exception as exc:
        st.error(f"Failed to parse circuit:\n\n```\n{exc}\n```")
        return

    metrics = compute_metrics(qc)
    weights = get_weights(conn)
    score = compute_score(metrics, **weights)

    with st.spinner("Verifying functional equivalence with benchmark (building unitary)…"):
        verified, verify_msg = verify_equivalence(qc, benchmark)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Qubits", metrics["qubit_count"])
    c2.metric("Depth", metrics["depth"])
    c3.metric("Gate count", metrics["gate_count"])
    c4.metric("Score", f"{score:.2f}")

    if verified:
        st.success(f"✅ {verify_msg}")
    else:
        st.error(f"❌ {verify_msg}")

    sid = insert_submission(
        conn,
        team_name=team_name,
        submitted_at=now_utc_iso(),
        qubit_count=metrics["qubit_count"],
        depth=metrics["depth"],
        gate_count=metrics["gate_count"],
        score=score,
        w1=weights["w1"],
        w2=weights["w2"],
        w3=weights["w3"],
        filename=file.name,
        circuit_text=text,
        verified=1 if verified else 0,
        verify_message=verify_msg,
    )

    if verified:
        st.balloons()
        st.info(f"Submission #{sid} recorded. Your best score will appear on the scoreboard.")
    else:
        st.warning(
            f"Submission #{sid} saved as **unverified** — it will not appear on the "
            "public scoreboard until an instructor manually approves it in the admin panel."
        )


def page_admin(conn):
    st.title("🔧 Admin")

    if not st.session_state.get("is_admin"):
        pw = st.text_input("Admin password", type="password")
        if st.button("Unlock"):
            if pw == ADMIN_PASSWORD:
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    # Weights
    weights = get_weights(conn)
    st.subheader("Scoring weights")
    with st.form("weights_form"):
        c1, c2, c3 = st.columns(3)
        w1 = c1.number_input("w1 · Qubit count", value=float(weights["w1"]), step=1.0, format="%.4f")
        w2 = c2.number_input("w2 · Depth", value=float(weights["w2"]), step=1.0, format="%.4f")
        w3 = c3.number_input("w3 · Gate count", value=float(weights["w3"]), step=1.0, format="%.4f")
        rescore = st.checkbox("Rescore all existing submissions with new weights", value=True)
        saved = st.form_submit_button("Save weights", type="primary")
    if saved:
        set_weights(conn, w1, w2, w3)
        if rescore:
            rescore_all(conn, w1, w2, w3)
        st.success("Weights updated.")
        st.rerun()

    # Submissions
    st.subheader("All submissions")
    rows = all_submissions(conn)
    if not rows:
        st.info("No submissions yet.")
    else:
        df = pd.DataFrame([dict(r) for r in rows])
        show_cols = [
            "id", "team_name", "submitted_at", "qubit_count", "depth",
            "gate_count", "score", "verified", "filename",
        ]
        st.dataframe(df[show_cols], hide_index=True, use_container_width=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        col_dl1, col_dl2 = st.columns(2)
        col_dl1.download_button(
            "Download submissions (CSV)", csv_bytes, "submissions.csv", "text/csv"
        )
        with open(DB_PATH, "rb") as f:
            col_dl2.download_button(
                "Download raw database (SQLite)",
                f.read(),
                "scoreboard.db",
                "application/octet-stream",
            )

        st.markdown("---")
        st.subheader("Manual controls")
        tc1, tc2 = st.columns([2, 1])
        with tc1:
            sid = st.number_input(
                "Submission ID", min_value=1, step=1, value=int(df["id"].max())
            )
        with tc2:
            action = st.selectbox("Action", ["Verify", "Unverify", "Delete"])
        if st.button("Apply"):
            if action == "Delete":
                delete_submission(conn, int(sid))
                st.success(f"Deleted submission {int(sid)}.")
            else:
                set_verified(conn, int(sid), action == "Verify")
                st.success(f"Submission {int(sid)} marked {action.lower()}ed.")
            st.rerun()

        # Per-row detail viewer
        st.markdown("---")
        st.subheader("Inspect submission")
        inspect_id = st.number_input(
            "View details for submission ID",
            min_value=1,
            step=1,
            value=int(df["id"].max()),
            key="inspect_id",
        )
        match = df[df["id"] == int(inspect_id)]
        if len(match):
            row = match.iloc[0]
            st.write(
                {
                    "team": row["team_name"],
                    "submitted_at": row["submitted_at"],
                    "qubits": int(row["qubit_count"]),
                    "depth": int(row["depth"]),
                    "gates": int(row["gate_count"]),
                    "score": float(row["score"]),
                    "weights": (float(row["w1"]), float(row["w2"]), float(row["w3"])),
                    "verified": bool(row["verified"]),
                    "verify_message": row["verify_message"],
                    "filename": row["filename"],
                }
            )
            with st.expander("Circuit source"):
                st.code(row["circuit_text"] or "", language="text")

    if st.button("Lock admin"):
        st.session_state["is_admin"] = False
        st.rerun()


def main():
    conn = get_db()
    page = st.sidebar.radio("Page", ["🏆 Scoreboard", "📤 Submit", "🔧 Admin"])
    if page == "🏆 Scoreboard":
        page_scoreboard(conn)
    elif page == "📤 Submit":
        page_submit(conn)
    else:
        page_admin(conn)
    st.sidebar.markdown("---")
    st.sidebar.caption("COE 530 · Term 252 · KFUPM")


if __name__ == "__main__":
    main()
