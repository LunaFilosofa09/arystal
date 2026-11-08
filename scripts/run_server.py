"""Start the Arystal web server. It listens on this computer only (127.0.0.1).

    python scripts/run_server.py                # then open http://127.0.0.1:8000
    python scripts/run_server.py --port 8010
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from arystal.server.app import create_app  # noqa: E402

LOCAL_ADDRESS = "127.0.0.1"
DEFAULT_PORT = 8000


def main() -> None:
    """Read the options and serve."""
    parser = argparse.ArgumentParser(description="Arystal web server (local use only).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    arguments = parser.parse_args()
    print(f"Arystal server: http://{LOCAL_ADDRESS}:{arguments.port}   (API docs at /docs). Stop it with Ctrl+C.")
    uvicorn.run(create_app(), host=LOCAL_ADDRESS, port=arguments.port, log_level="warning")


if __name__ == "__main__":
    main()
