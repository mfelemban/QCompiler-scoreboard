"""Wrapper: invokes Ryadh's COE530_General_Optimizer.run on INPUT.qasm."""
import sys
from pathlib import Path

ROOT = Path("/Users/mfelemban/Dropbox/KFUPM/Teaching/T252/COE530/Project/Groups/Ryadh")
sys.path.insert(0, str(ROOT))

from COE530_General_Optimizer import run  # noqa: E402

inp, out = sys.argv[1], sys.argv[2]
run(inp, output_path=out, coupling_map=None)
print(f"ryadh: wrote {out}")
