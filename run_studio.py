"""Convenience script to launch RF Origami Design Studio.

Usage:
    python run_studio.py
    python run_studio.py --port 8080
"""

import argparse
import os
import sys
import webbrowser

# Ensure script directory is always in Python module search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rf_origami.web.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="RF Origami Design Studio")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the web browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    run_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
