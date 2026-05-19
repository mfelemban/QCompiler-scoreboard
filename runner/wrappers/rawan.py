"""Wrapper: runs Rawan's notebook pipeline on INPUT.qasm."""
import os, re, sys, tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
# pytket tries to write ~/.config/pytket which is not writable on this host.
os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp(prefix="pytket_cfg_"))
CONVERTED = Path(__file__).parent.parent / "converted" / "rawan.py"
inp, out = sys.argv[1], sys.argv[2]

src = CONVERTED.read_text()
src = re.sub(r"^\s*%[a-zA-Z]+.*$", "", src, flags=re.MULTILINE)
src = re.sub(r"^(.*\.draw\(.*\))$", r"# stripped: \1", src, flags=re.MULTILINE)
src = re.sub(r"^(plt\..*)$", r"# stripped: \1", src, flags=re.MULTILINE)
src = re.sub(r"^(nx\.draw.*)$", r"# stripped: \1", src, flags=re.MULTILINE)
src = src.replace(
    'benchmark_circuit = "benchmark_circuit.qasm"',
    f'benchmark_circuit = {inp!r}',
)
src = src.replace(
    'OUTPUT_FILE = "test_score.qasm"',
    f'OUTPUT_FILE = {out!r}',
)

g = {"__name__": "__rawan_wrapper__", "__file__": str(CONVERTED)}
exec(compile(src, str(CONVERTED), "exec"), g)
print(f"rawan: wrote {out}")
