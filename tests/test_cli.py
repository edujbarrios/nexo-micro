import json
import os
import subprocess
import sys


def test_cli_bench_bytes():
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-m", "nexo_micro", "bench", "--bytes-only", "--repeats", "2"],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    totals = json.loads(result.stdout)
    assert totals["unit"] == "UTF-8 bytes (not tokens)"
    assert totals["messages"] == 8
    assert totals["micro"] < totals["json_compact"]
