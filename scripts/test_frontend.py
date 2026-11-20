"""Run the two UI scenarios with the same isolated environment as API tests."""

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.conftest import application


def main():
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("npm is required")
    with application() as (app, _):
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Test API failed to start")
                time.sleep(0.05)
            return subprocess.run(
                [npm, "test"], cwd=ROOT / "frontend", timeout=120, check=False
            ).returncode
        finally:
            server.should_exit = True
            thread.join(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
