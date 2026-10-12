"""Run the real HTTP demonstration with an isolated database and local server.

    python demo/verify_local.py

The server and temporary SQLite database are removed on exit; JSON/Markdown
evidence remains in demo/output. Requires the application's installed packages.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        output = ROOT / "demo" / "output"
        output.mkdir(parents=True, exist_ok=True)
        with (output / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--workers",
                    "1",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "CASE_DATABASE_PATH": str(Path(tmp) / "cases.sqlite3"),
                },
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError(
                            "Server stopped; inspect demo/output/server.log"
                        )
                    try:
                        with urlopen(base + "/openapi.json", timeout=1) as response:
                            if response.status == 200:
                                break
                    except (URLError, TimeoutError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Server did not become ready")
                subprocess.run(
                    [sys.executable, "demo/run_pipeline.py", "--base-url", base],
                    cwd=ROOT,
                    check=True,
                )
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    main()
