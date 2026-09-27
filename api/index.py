"""Vercel Serverless Function entrypoint."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERA_BOT = ROOT / "vera-bot"

if str(VERA_BOT) not in sys.path:
    sys.path.insert(0, str(VERA_BOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot import app
