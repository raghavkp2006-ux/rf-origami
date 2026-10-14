"""Vercel Serverless Function handler for RF Origami Design Studio.

Bridges Vercel Serverless Python runtime directly into the native
OrigamiRequestHandler to handle all /api/* requests.
"""

from __future__ import annotations
import os
import sys

# Ensure project root is in Python sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from rf_origami.web.server import OrigamiRequestHandler  # noqa: E402


class handler(OrigamiRequestHandler):
    """Vercel serverless request handler."""
    pass
