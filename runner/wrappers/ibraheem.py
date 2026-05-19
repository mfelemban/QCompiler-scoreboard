"""Wrapper: invokes Ibraheem's iter_all pipeline on INPUT.qasm.

Replicates iter_all.main() but with paths from sys.argv and a smaller iter
budget so it stays under the runner timeout.
"""
import sys
from pathlib import Path
from qiskit import qasm3

ROOT = Path("/Users/mfelemban/Dropbox/KFUPM/Teaching/T252/COE530/Project/Groups/Ibraheem")
sys.path.insert(0, str(ROOT))

from recognize_toffoli import collapse_toffolis  # noqa: E402
from iter_all import one_pass, score_qc  # noqa: E402

MAX_ITERS = 8  # iter_all.main uses 15; trim to fit timeout

inp, out = sys.argv[1], sys.argv[2]
qc_orig = qasm3.load(inp)
best = collapse_toffolis(qc_orig)
best_score = score_qc(best)[3]
prev = best_score
for it in range(MAX_ITERS):
    cand = one_pass(best, qc_orig)
    s = score_qc(cand)[3]
    if s < best_score:
        best_score, best = s, cand
    elif s == prev:
        break
    else:
        best = cand
    prev = s

with open(out, "w") as f:
    f.write(qasm3.dumps(best))
print(f"ibraheem: wrote {out} (score={best_score})")
