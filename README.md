# COE 530 Scoreboard

Public scoreboard for the **COE 530 — Quantum Computer & Architecture** (Term 252, KFUPM)
circuit-optimization project.

## What it does

1. Students upload an optimized OpenQASM 2.0/3.0 circuit.
2. Qiskit parses it and measures **qubit count**, **circuit depth**, **gate count**.
3. The app verifies **unitary equivalence** to the benchmark via `qiskit.quantum_info.Operator`.
4. Score: `Score = w1·Qubits + w2·Depth + w3·Gates` (weights set by instructor).
5. Every submission is logged in SQLite; the scoreboard ranks each team by their best verified submission.

## Local run

```bash
cd scoreboard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit
streamlit run app.py
```

Open <http://localhost:8501>.

## Deploy to Streamlit Community Cloud (free, public URL)

1. Create a **new public GitHub repo** and push the contents of this `scoreboard/` folder to its root.
2. Go to <https://share.streamlit.io> → sign in with GitHub → **New app**.
3. Pick the repo, branch, and set main file to `app.py`. Deploy.
4. Open the app's **⋮ → Settings → Secrets** and paste:
   ```toml
   class_password = "…"
   admin_password = "…"
   ```
5. Share the public URL on Blackboard.

If you prefer not to push secrets via the UI, you can also deploy to
**Hugging Face Spaces** (select the *Streamlit* template) with the same files.

## Pages

- **🏆 Scoreboard** — public, anonymous. Shows each team's best verified submission.
- **📤 Submit** — requires the class password. Uploads are scored & auto-verified live.
- **🎯 Final Test** — public, read-only. Shows each group's scores on the
  5 final-test benchmark circuits, plus a ranked total.
- **🔧 Admin** — requires the admin password. Configure weights, browse / verify /
  delete submissions, download a CSV or the raw SQLite file.

## Final test workflow

The final test runs each group's optimizer against 5 benchmark circuits of
escalating difficulty (`final_benchmarks/circuit_1_very_easy.qasm` …
`circuit_5_very_hard.qasm`). Two flows are supported.

### Manual flow (per-team)

The instructor runs the groups' submitted code locally to produce 5 optimized
QASM files per group, then records the scores with `submit_final.py`:

```bash
# Score one circuit for one team
python submit_final.py one --team TeamHadamard --circuit 1 \
    --file path/to/optimized_circuit_1.qasm

# Batch: folder of files named {team}_circuit{N}.qasm
python submit_final.py batch --dir path/to/optimized_outputs/
```

### Automated flow (runner/)

Live in the `Groups/` directory, the runner spawns per-group wrappers as
subprocesses, scores their output against each of the 5 benchmarks, and
upserts results to the DB:

```bash
python runner/run_final_test.py              # all groups, all 5 circuits
python runner/run_final_test.py ryadh        # one group, all 5 circuits
python runner/run_final_test.py ryadh c3 c5  # one group, specific circuits
PER_RUN_TIMEOUT=600 python runner/run_final_test.py fahad c5  # longer budget
```

Per-group wrappers live in `runner/wrappers/`; converted notebook sources in
`runner/converted/`; optimized outputs in `runner/outputs/`. After changing
`scoring.py`, recompute scores from existing outputs without re-running the
optimizers:

```bash
python runner/rescore_outputs.py --skip-verify
```

Re-running with the same `(team, circuit)` overwrites the previous score.
Scores use the weights currently configured in the admin panel and are
computed on the **fully decomposed** circuit, so custom gate definitions in
QASM output (e.g. clifford blocks, consolidated 2q unitaries) are unfolded
to primitive gates before counting depth and gate count.

## Automatic equivalence check — limits

The unitary check is exact but requires the submitted circuit to have the **same
qubit count** as the benchmark and **no mid-circuit measurements/resets**.
Circuits that use qubit reuse or ancilla reduction will fail the automatic
check — the admin panel lets the instructor manually mark them verified after
an out-of-band check.

## Data persistence note

SQLite lives on the app container's disk. Streamlit Cloud preserves this across
normal reboots, but a **redeploy (new git push)** resets the disk. Use the
admin **"Download raw database"** button to back up before redeploying. For
larger / longer-lived classes, swap SQLite for a managed store (Supabase
Postgres, Turso libSQL, etc.) — only `db.py` needs to change.

## Swapping the benchmark

Replace `benchmark_circuit.qasm` in this folder and redeploy. The app loads it
on startup and caches the parsed `QuantumCircuit`.
