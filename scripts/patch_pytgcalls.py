"""Wrap py-tgcalls' bare Groupcall* error imports in try/except.

py-tgcalls imports GroupcallForbidden / GroupcallInvalid from
pyrogram.errors, but pyrogram 2.0.106 (last official release) does not
define them. Wrapping the imports keeps voice calls working; the except
branch aliases the class to Exception. Idempotent.

Usage: venv/bin/python patch_pytgcalls.py <venv-dir>
"""
import glob
import re
import sys

venv = sys.argv[1] if len(sys.argv) > 1 else "venv"
pattern = re.compile(
    r"^from ((?:pyrogram|hydrogram|telethon)\.errors[\w.]*) import (Groupcall\w+)$"
)

for f in glob.glob(f"{venv}/**/pytgcalls/mtproto/*.py", recursive=True):
    with open(f) as fh:
        original = fh.read()
    lines = original.splitlines()
    out = []
    for i, line in enumerate(lines):
        m = pattern.match(line)
        prev = lines[i - 1].strip() if i else ""
        if m and prev != "try:":
            out.append(
                f"try:\n    from {m.group(1)} import {m.group(2)}\n"
                f"except ImportError:\n    {m.group(2)} = Exception"
            )
        else:
            out.append(line)
    patched = "\n".join(out) + ("\n" if original.endswith("\n") else "")
    if patched != original:
        with open(f, "w") as fh:
            fh.write(patched)
        print("patched:", f.split("site-packages/")[-1])
