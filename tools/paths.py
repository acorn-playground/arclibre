"""Shared paths for the maintained build; no historical experiment dependency."""
import os,pathlib
REPO=pathlib.Path(__file__).resolve().parents[1]
ROOT=pathlib.Path(os.environ.get('OPEN_ARCHIMEDES_OUTPUT',str(REPO/'build/rom'))).resolve()
SRC=REPO/'src'
HOST=REPO/'build/host'
TOOLS=REPO/'build/toolchain'
