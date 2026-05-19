"""Wrapper: invokes Abdulrahman's pipeline.run_pipeline on INPUT.qasm."""
import sys
from pathlib import Path

ROOT = Path("/Users/mfelemban/Dropbox/KFUPM/Teaching/T252/COE530/Project/Groups/Abdulrahman/Code and circuits")
sys.path.insert(0, str(ROOT))

from pipeline import parse_qasm3, run_pipeline, write_qasm3  # noqa: E402

inp, out = sys.argv[1], sys.argv[2]
nq, ops = parse_qasm3(inp)
opt_ops, _ = run_pipeline(nq, ops, verbose=False)
write_qasm3(out, nq, opt_ops)
print(f"abdulrahman: wrote {out} ({len(opt_ops)} ops)")
